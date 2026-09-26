import secrets
from collections import Counter
from datetime import timedelta
from uuid import UUID

from app.core.config import settings
from app.models.domain import (
    AgentDecision,
    ConversationTurn,
    DialogueDecision,
    DialogueSnapshot,
    Difficulty,
    FeedbackComparison,
    GenerationMetadata,
    ResearchEvent,
    Role,
    RolePlayStatus,
    Session,
    StudyQuestionnaire,
    StudyRecord,
    utcnow,
)
from app.repositories.base import Repository
from app.safety.crisis import CRISIS_RESPONSE, contains_crisis_language
from app.services import workload_dialogue
from app.services.affect_service import (
    ExponentialStateTracker,
    RuleBasedCognitiveAnalyzer,
    RuleBasedEmotionAnalyzer,
)
from app.services.eligibility import has_current_eligibility
from app.services.interfaces import CognitiveAnalyzer, EmotionAnalyzer, ResponseGenerator, StrategySelector
from app.services.llm_service import OpenAIResponseGenerator
from app.services.roleplay_service import SCENARIOS, RolePlayService
from app.services.strategy_service import RuleBasedStrategySelector, ScoredStrategySelector
from app.services.study_tasks import PROTOCOL_REQUIRED_SCENARIOS, select_required_attempts


def dialogue_snapshot(session: Session) -> DialogueSnapshot:
    state = session.roleplay
    assert state and state.dialogue
    return DialogueSnapshot(dialogue=state.dialogue.model_copy(deep=True), turn=state.turn,
        status=state.status, completion_reason=state.completion_reason,
        success_progress=state.success_progress, difficulty=state.difficulty,
        cooperation=state.cooperation, emotion_state=session.emotion_state.model_copy(deep=True))


class SessionNotFoundError(KeyError): pass
class QuestionnaireConflictError(ValueError): pass


class ConversationService:
    def __init__(self, repository: Repository, analyzer: EmotionAnalyzer | None = None, cognitive_analyzer: CognitiveAnalyzer | None = None, selector: StrategySelector | None = None, generator: ResponseGenerator | None = None) -> None:
        self.repository, self.analyzer = repository, analyzer or RuleBasedEmotionAnalyzer()
        self.cognitive_analyzer = cognitive_analyzer or RuleBasedCognitiveAnalyzer()
        self.state_tracker = ExponentialStateTracker()
        self.selector, self.generator = selector or RuleBasedStrategySelector(), generator or OpenAIResponseGenerator()
        self.roleplays = RolePlayService()
    async def create_session(self, user_id: UUID) -> Session:
        session = Session(user_id=user_id)
        session.research_events.append(ResearchEvent(name="session_created"))
        await self.save(session)
        return session
    async def get_session(self, session_id: UUID, user_id: UUID) -> Session:
        session = await self.repository.get_session(session_id, user_id)
        if not session: raise SessionNotFoundError
        return session
    async def list_sessions(self, user_id: UUID) -> list[Session]: return await self.repository.list_sessions(user_id)
    async def backfill_active_study_records(self) -> None:
        for user in await self.repository.list_users():
            if not (
                user.pilot_enrolled_at
                and user.study_consent
                and has_current_eligibility(user)
                and user.study_consent.version == settings.study_consent_version
                and user.study_consent.protocol_version == settings.study_protocol_version
                and not user.study_withdrawal
            ):
                continue
            for session in await self.repository.list_sessions(user.id):
                await self.sync_study_record(session)
    async def delete_session(self, session_id: UUID, user_id: UUID) -> None:
        if not await self.repository.delete_session(session_id, user_id): raise SessionNotFoundError
    async def rename_session(self, session_id: UUID, user_id: UUID, title: str) -> Session:
        session = await self.get_session(session_id, user_id)
        session.title = " ".join(title.split())
        await self.save(session)
        return session
    async def save_takeaway(self, session_id: UUID, user_id: UUID, takeaway: str) -> Session:
        session = await self.get_session(session_id, user_id)
        session.takeaway = " ".join(takeaway.split())
        session.research_events.append(ResearchEvent(name="takeaway_saved", properties={"length": len(session.takeaway)}))
        await self.save(session)
        return session
    async def save(self, session: Session) -> None:
        session.updated_at, session.expires_at = utcnow(), utcnow() + timedelta(days=settings.session_retention_days)
        await self.repository.save_session(session)
        await self.sync_study_record(session)
    async def sync_study_record(self, session: Session) -> None:
        lifecycle = await self.repository.get_study_lifecycle(settings.study_protocol_version)
        if lifecycle and (lifecycle.dataset_frozen_at or lifecycle.freeze_token):
            return
        today = utcnow().date()
        if lifecycle and lifecycle.start_date and today < lifecycle.start_date:
            return
        if lifecycle and lifecycle.end_date and today > lifecycle.end_date:
            return
        user = await self.repository.get_user(session.user_id)
        if not (
            user
            and user.pilot_enrolled_at
            and user.study_consent
            and has_current_eligibility(user)
            and user.study_consent.version == settings.study_consent_version
            and user.study_consent.protocol_version == settings.study_protocol_version
            and not user.study_withdrawal
            and not user.study_excluded_at
        ):
            return
        consented_at = user.study_consent.accepted_at
        roleplay = session.roleplay if session.roleplay and session.roleplay.started_at >= consented_at else None
        feedback = (
            session.feedback
            if session.feedback and roleplay and roleplay.completed_at and roleplay.completed_at >= consented_at
            else None
        )
        questionnaires = {
            phase: answer
            for phase, answer in session.questionnaires.items()
            if answer.submitted_at >= consented_at
        }
        measurement_end = roleplay.measurement_ended_at if roleplay else None
        if roleplay and roleplay.completed_at and measurement_end is None:
            # Legacy completions predate the explicit boundary. Include the closing
            # reply paired with a pre-completion message, never later reflection.
            measurement_end = roleplay.completed_at
            for index, turn in enumerate(session.turns):
                if (turn.role == Role.ASSISTANT and index > 0
                        and session.turns[index - 1].role == Role.USER
                        and session.turns[index - 1].created_at <= roleplay.completed_at):
                    measurement_end = max(measurement_end, turn.created_at)
        events = [event for event in session.research_events
                  if event.created_at >= consented_at
                  and (measurement_end is None or event.created_at <= measurement_end
                       or event.name.startswith("questionnaire_"))]
        measured_turns = [turn for turn in session.turns if turn.created_at >= consented_at
                          and (measurement_end is None or turn.created_at <= measurement_end)]
        post_consent_turn_count = len(measured_turns)
        last_activity = (max([measurement_end, *[event.created_at for event in events],
                              *[answer.submitted_at for answer in questionnaires.values()]])
                         if measurement_end else session.updated_at)
        if not (post_consent_turn_count or roleplay or questionnaires or events):
            return
        assistant_turns = [turn for turn in measured_turns if turn.role == Role.ASSISTANT]
        await self.repository.save_study_record(StudyRecord(
            user_id=user.id,
            participant_id=user.participant_id,
            session_id=session.id,
            consent_version=user.study_consent.version,
            protocol_version=user.study_consent.protocol_version,
            enrolled_at=user.pilot_enrolled_at,
            session_created_at=session.created_at,
            last_activity_at=last_activity,
            retention_expires_at=last_activity + timedelta(days=settings.study_record_retention_days),
            turn_count=post_consent_turn_count,
            attempt_purpose=roleplay.attempt_purpose if roleplay else "additional",
            required_task_id=roleplay.required_task_id if roleplay else None,
            scenario_id=roleplay.scenario_id if roleplay else None,
            difficulty=roleplay.difficulty_level if roleplay else None,
            completion_reason=roleplay.completion_reason if roleplay else None,
            feedback_metrics=feedback.metrics if feedback else [],
            feedback_generation_source=feedback.generation_source if feedback else None,
            roleplay_started_at=roleplay.started_at if roleplay else None,
            roleplay_completed_at=roleplay.completed_at if roleplay else None,
            generation_source_counts=dict(Counter(
                turn.generation.source if turn.generation else "unrecorded" for turn in assistant_turns
            )),
            fallback_reason_counts=dict(Counter(
                turn.generation.fallback_reason for turn in assistant_turns
                if turn.generation and turn.generation.fallback_reason
            )),
            questionnaires=questionnaires,
            events=events,
            updated_at=utcnow(),
        ))
    async def chat(self, session_id: UUID, user_id: UUID, message: str) -> tuple[ConversationTurn, AgentDecision, Session]:
        session = await self.get_session(session_id, user_id)
        rehearsal_running = session.roleplay and session.roleplay.status in {RolePlayStatus.ACTIVE, RolePlayStatus.PAUSED}
        before = dialogue_snapshot(session) if rehearsal_running and session.roleplay.dialogue else None
        plan = None
        if session.post_questionnaire_token:
            session.post_questionnaire_token = None
            session.research_events.append(ResearchEvent(name="questionnaire_post_closed"))
        if session.title == "New reflection":
            clean = " ".join(message.split())
            session.title = clean[:57].rstrip(" ,.;:-") + ("…" if len(clean) > 57 else "")
        crisis = contains_crisis_language(message)
        if not crisis and isinstance(self.generator, OpenAIResponseGenerator): crisis = await self.generator.moderate(message)
        state = self.state_tracker.update(session.emotion_state, self.analyzer.analyze(message))
        assessment, session.emotion_state = self.cognitive_analyzer.analyze(message, crisis), state
        state.resistance = assessment.resistance
        if isinstance(self.selector, ScoredStrategySelector):
            strategy_decision = self.selector.decide(state, assessment)
            strategy, strategy_scores, reasons = strategy_decision.strategy, strategy_decision.scores, strategy_decision.reasons
        else:
            strategy, strategy_scores, reasons = self.selector.select(state, assessment), {}, []
        session.turns.append(ConversationTurn(role=Role.USER, content=message, emotion_state=state))
        roleplay_action = "none"
        if crisis:
            content, metadata = CRISIS_RESPONSE, GenerationMetadata(source="safety_response")
            if session.roleplay and session.roleplay.status in {RolePlayStatus.ACTIVE, RolePlayStatus.PAUSED}:
                session.roleplay.status, session.roleplay.completion_reason = RolePlayStatus.INTERRUPTED, "safety_interruption"
                session.roleplay.completed_at = utcnow()
        elif session.roleplay and session.roleplay.status == RolePlayStatus.ACTIVE:
            plan = self.roleplays.plan_response(session.roleplay, message, state)
            session.roleplay.evidence[-1].conversation_turn_id = session.turns[-1].id
            roleplay_action = plan.action
            if plan.completed:
                content, metadata = plan.fallback_text, GenerationMetadata(source="deterministic_roleplay")
                await self.complete_feedback(session)
            elif isinstance(self.generator, OpenAIResponseGenerator):
                content, metadata = await self.generator.generate_roleplay(
                    session,
                    session.roleplay.scenario or SCENARIOS[session.roleplay.scenario_id],
                    plan.action,
                    plan.fallback_text,
                )
            else:
                content, metadata = plan.fallback_text, GenerationMetadata(source="deterministic_roleplay")
        else: content, metadata = await self.generator.generate(session, message, strategy)
        turn = ConversationTurn(role=Role.ASSISTANT, content=content, strategy=strategy, generation=metadata)
        session.turns.append(turn)
        if before and (plan or crisis):
            roleplay = session.roleplay
            roleplay.decisions.append(DialogueDecision(
                user_turn_id=session.turns[-2].id, assistant_turn_id=turn.id,
                before=before, after=dialogue_snapshot(session),
                action=plan.action if plan else "safety_interruption",
                reason_codes=list(plan.reason_codes) if plan else ["safety_interruption"],
                evidence_turn_ids=[e.conversation_turn_id for e in roleplay.evidence if e.conversation_turn_id],
                scenario_version=roleplay.scenario_version, policy_version=roleplay.policy_version,
                scoring_version=roleplay.scoring_version, generation=metadata.model_copy(deep=True)))
        session.research_events.append(ResearchEvent(
            name="message_completed",
            properties={
                "message_length": len(message),
                "crisis_detected": crisis,
                "strategy": strategy.value,
                "roleplay_active": bool(session.roleplay and session.roleplay.status == RolePlayStatus.ACTIVE),
                "roleplay_action": roleplay_action,
            },
        ))
        if rehearsal_running and session.roleplay.completed_at:
            # The closing assistant reply and its event belong to the rehearsal.
            session.roleplay.measurement_ended_at = utcnow()
        await self.save(session)
        return turn, AgentDecision(emotion_state=state, cognitive_assessment=assessment, strategy=strategy, strategy_scores=strategy_scores, decision_reasons=reasons, analyzer_version=getattr(self.analyzer, "version", "unknown")), session
    async def start_roleplay(self, session_id: UUID, user_id: UUID, scenario_id: str, level: Difficulty, custom=None, pre_ratings: dict | None = None, pre_skipped: bool = False, attempt_purpose: str = "additional", required_task_id: str | None = None):
        session = await self.get_session(session_id, user_id)
        state, scenario = self.roleplays.start(scenario_id, level, custom)
        if attempt_purpose not in {"required", "additional", "retry"}:
            raise ValueError("Unknown attempt purpose")
        if required_task_id is not None and (required_task_id not in PROTOCOL_REQUIRED_SCENARIOS or required_task_id != scenario_id):
            raise ValueError("Required task association must match a standard scenario")
        if attempt_purpose == "additional" and required_task_id is not None:
            raise ValueError("Additional practice cannot claim a required task")
        if attempt_purpose == "required":
            if required_task_id != scenario_id or scenario_id not in PROTOCOL_REQUIRED_SCENARIOS or level != Difficulty.INTERMEDIATE:
                raise ValueError("Required study tasks must match the checklist at intermediate difficulty")
            user = await self.repository.get_user(user_id)
            if not (user and user.pilot_enrolled_at and user.study_consent and has_current_eligibility(user)
                    and user.study_consent.version == settings.study_consent_version
                    and user.study_consent.protocol_version == settings.study_protocol_version
                    and not user.study_withdrawal and not user.study_excluded_at):
                raise ValueError("Current study enrollment is required")
            lifecycle = await self.repository.get_study_lifecycle(settings.study_protocol_version)
            today = utcnow().date()
            if lifecycle and (lifecycle.dataset_frozen_at or lifecycle.freeze_token
                              or (lifecycle.start_date and today < lifecycle.start_date)
                              or (lifecycle.end_date and today > lifecycle.end_date)):
                raise ValueError("Study collection is closed; choose additional practice")
            if required_task_id in select_required_attempts(await self.repository.list_study_records(user_id)):
                raise ValueError("This required task already has an attempt. Resume it or choose additional practice.")
        state.attempt_purpose, state.required_task_id = attempt_purpose, required_task_id
        if attempt_purpose == "additional" and scenario_id == "workload" and level == Difficulty.INTERMEDIATE and custom is None:
            workload_dialogue.enable(state)
            scenario = state.scenario
        if pre_ratings is not None and pre_skipped:
            raise ValueError("Choose either pre-ratings or skip")
        pre = StudyQuestionnaire(phase="pre", **pre_ratings) if pre_ratings is not None else None
        # A populated session belongs to its existing reflection/rehearsal. Reuse only
        # an unused workspace; retries must never replace history or study records.
        if session.turns or session.roleplay or session.feedback or session.takeaway or "post" in session.questionnaires:
            session = Session(user_id=user_id)
            session.research_events.append(ResearchEvent(name="session_created"))
        if not pre and not pre_skipped and "pre" not in session.questionnaires and "pre" not in session.questionnaire_skips:
            raise ValueError("Answer or explicitly skip the pre-questionnaire before starting")
        if pre is not None and ("pre" in session.questionnaires or "pre" in session.questionnaire_skips):
            raise QuestionnaireConflictError("The pre-questionnaire decision is already recorded")
        if pre_skipped and "pre" in session.questionnaires:
            raise QuestionnaireConflictError("The pre-questionnaire decision is already recorded")
        if pre_skipped and "pre" not in session.questionnaire_skips:
            session.questionnaire_skips["pre"] = utcnow()
            session.research_events.append(ResearchEvent(name="questionnaire_pre_skipped"))
        if pre is not None:
            session.questionnaires["pre"] = pre
            session.research_events.append(ResearchEvent(name="questionnaire_pre_submitted"))
        state.started_at = utcnow()
        session.roleplay, session.feedback = state, None
        session.title = scenario.title
        session.turns = []
        session.emotion_state = self.analyzer.analyze("")
        turn = ConversationTurn(role=Role.ASSISTANT, content=scenario.opening_line, generation=GenerationMetadata(source="scenario_opening"))
        session.turns.append(turn)
        session.research_events.append(ResearchEvent(
            name="roleplay_started",
            properties={"scenario_id": scenario_id, "difficulty": level.value},
        ))
        await self.save(session)
        return session, scenario, turn
    async def set_roleplay_status(self, session_id: UUID, user_id: UUID, action: str):
        session = await self.get_session(session_id, user_id)
        if not session.roleplay: raise ValueError("No role-play")
        if action == "pause" and session.roleplay.status == RolePlayStatus.ACTIVE: session.roleplay.status = RolePlayStatus.PAUSED
        elif action == "resume" and session.roleplay.status == RolePlayStatus.PAUSED: session.roleplay.status = RolePlayStatus.ACTIVE
        elif action == "finish" and session.roleplay.status in {RolePlayStatus.ACTIVE, RolePlayStatus.PAUSED}: self.roleplays.finish(session.roleplay); await self.complete_feedback(session)
        else: raise ValueError("Invalid role-play transition")
        session.research_events.append(ResearchEvent(
            name=f"roleplay_{action}",
            properties={"scenario_id": session.roleplay.scenario_id},
        ))
        if action == "finish":
            session.roleplay.measurement_ended_at = utcnow()
        await self.save(session); return session
    async def rewind_roleplay(self, session_id: UUID, user_id: UUID) -> tuple[str, Session]:
        session = await self.get_session(session_id, user_id)
        state = session.roleplay
        if "post" in session.questionnaires or "post" in session.questionnaire_skips:
            raise ValueError("Start a new attempt to retry after recording post-ratings or a skip")
        if not state or not state.evidence or len(session.turns) < 3:
            raise ValueError("There is no role-play exchange to rewind")
        # Only remove the exchange that produced the latest rehearsal evidence.
        # Legacy evidence has no reliable link, so preserve its history as well.
        if (session.turns[-1].role != Role.ASSISTANT
                or session.turns[-2].role != Role.USER
                or state.evidence[-1].conversation_turn_id != session.turns[-2].id):
            raise ValueError(
                "The latest conversation exchange is not linked to this rehearsal turn. "
                "Your history has been kept. To start a new attempt, choose Finish & review "
                "if the rehearsal is still active, then Practise again."
            )
        session.post_questionnaire_token = None
        session.turns.pop()
        user_turn = session.turns.pop()
        if state.dialogue is not None:
            decision = state.decisions.pop()
            snapshot = decision.before
            state.dialogue = snapshot.dialogue.model_copy(deep=True)
            state.turn, state.success_progress = snapshot.turn, snapshot.success_progress
            state.difficulty, state.cooperation = snapshot.difficulty, snapshot.cooperation
            state.evidence = state.evidence[:snapshot.turn]
            state.status = RolePlayStatus.ACTIVE
            state.completion_reason = state.completed_at = state.measurement_ended_at = None
            session.feedback = None
            session.emotion_state = snapshot.emotion_state.model_copy(deep=True)
            session.research_events = [e for e in session.research_events if e.created_at < user_turn.created_at]
            session.research_events.append(ResearchEvent(name="roleplay_rewound", properties={"scenario_id": state.scenario_id}))
            await self.save(session)
            return user_turn.content, session
        state.evidence.pop()
        state.turn = len(state.evidence)
        state.status = RolePlayStatus.ACTIVE
        state.completion_reason = None
        state.completed_at = None
        state.measurement_ended_at = None
        session.feedback = None
        scenario = state.scenario or SCENARIOS[state.scenario_id]
        checks = {
            "concrete_request": any(e.concrete_request for e in state.evidence),
            "specific_detail": any(e.specific_detail for e in state.evidence),
            "maintained_boundary": any(e.maintained_boundary for e in state.evidence),
            "i_statement": any(e.i_statement for e in state.evidence),
            "no_blame": not any(e.blame_language for e in state.evidence),
        }
        if state.scenario_id == "boundary":
            required = 1 if state.difficulty_level == Difficulty.BEGINNER else 2
            state.success_progress = min(1, sum(e.maintained_boundary for e in state.evidence) / required)
        elif state.evidence:
            state.success_progress = sum(checks.get(key, False) for key in scenario.success_conditions) / len(scenario.success_conditions)
        else:
            state.success_progress = 0
        session.emotion_state = user_turn.emotion_state or self.analyzer.analyze("")
        session.research_events.append(ResearchEvent(name="roleplay_rewound", properties={"scenario_id": state.scenario_id}))
        await self.save(session)
        return user_turn.content, session
    async def submit_questionnaire(
        self, session_id: UUID, user_id: UUID, phase: str, values: dict,
        skipped: bool = False, post_token: str | None = None,
    ) -> StudyQuestionnaire | None:
        if phase not in {"pre", "post"}:
            raise ValueError("Questionnaire phase must be pre or post")
        session = await self.get_session(session_id, user_id)
        if phase in session.questionnaires or phase in session.questionnaire_skips:
            raise QuestionnaireConflictError("This questionnaire decision is already recorded and cannot be changed")
        if phase == "pre" and session.roleplay:
            raise QuestionnaireConflictError("Pre-ratings must be recorded before the rehearsal starts")
        if phase == "post" and (
            not session.roleplay or session.roleplay.status != RolePlayStatus.COMPLETED
            or not session.roleplay.completed_at or not session.feedback
            or not post_token or post_token != session.post_questionnaire_token
        ):
            raise QuestionnaireConflictError("Post-ratings are only available immediately after completing the rehearsal")
        answers = {key: value for key, value in values.items() if value is not None}
        required = {"confidence", "anxiety"} if phase == "pre" else {"confidence", "realism", "usefulness"}
        if (skipped and answers) or (not skipped and set(answers) != required):
            raise ValueError("Answer every question for this phase, or explicitly skip without ratings")
        questionnaire = None if skipped else StudyQuestionnaire(phase=phase, **answers)
        if questionnaire:
            session.questionnaires[phase] = questionnaire
        else:
            session.questionnaire_skips[phase] = utcnow()
        if phase == "post":
            session.post_questionnaire_token = None
        session.research_events.append(ResearchEvent(name=f"questionnaire_{phase}_{'skipped' if skipped else 'submitted'}"))
        await self.save(session)
        return questionnaire

    async def close_post_questionnaire(self, session_id: UUID, user_id: UUID) -> None:
        session = await self.get_session(session_id, user_id)
        if session.post_questionnaire_token:
            session.post_questionnaire_token = None
            session.research_events.append(ResearchEvent(name="questionnaire_post_closed"))
            await self.save(session)

    async def complete_feedback(self, session: Session) -> None:
        if not session.roleplay: return
        feedback = self.roleplays.feedback(session.roleplay)
        previous = next((item for item in await self.repository.list_sessions(session.user_id) if item.id != session.id and item.feedback and item.feedback.scenario_id == session.roleplay.scenario_id and item.roleplay and item.roleplay.scoring_version == session.roleplay.scoring_version), None)
        if previous and previous.feedback:
            old = {metric.name: metric.score for metric in previous.feedback.metrics}
            feedback.compared_with_session_id = previous.id
            feedback.comparisons = [FeedbackComparison(name=metric.name, current_score=metric.score, previous_score=old[metric.name], change=metric.score-old[metric.name]) for metric in feedback.metrics if metric.name in old]
        if isinstance(self.generator, OpenAIResponseGenerator) and session.roleplay.dialogue is None: feedback = await self.generator.phrase_feedback(feedback)
        feedback.session_id = session.id
        session.feedback = feedback
        session.post_questionnaire_token = secrets.token_urlsafe(32)
