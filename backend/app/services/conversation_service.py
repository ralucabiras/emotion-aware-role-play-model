from datetime import timedelta
from uuid import UUID

from app.core.config import settings
from app.models.domain import (
    AgentDecision,
    ConversationTurn,
    Difficulty,
    FeedbackComparison,
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
from app.services.affect_service import (
    ExponentialStateTracker,
    RuleBasedCognitiveAnalyzer,
    RuleBasedEmotionAnalyzer,
)
from app.services.interfaces import CognitiveAnalyzer, EmotionAnalyzer, ResponseGenerator, StrategySelector
from app.services.llm_service import OpenAIResponseGenerator
from app.services.roleplay_service import SCENARIOS, RolePlayService
from app.services.strategy_service import RuleBasedStrategySelector, ScoredStrategySelector


class SessionNotFoundError(KeyError): pass


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
        user = await self.repository.get_user(session.user_id)
        if not (
            user
            and user.pilot_enrolled_at
            and user.study_consent
            and user.study_consent.version == settings.study_consent_version
            and user.study_consent.protocol_version == settings.study_protocol_version
            and not user.study_withdrawal
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
        events = [event for event in session.research_events if event.created_at >= consented_at]
        post_consent_turn_count = sum(turn.created_at >= consented_at for turn in session.turns)
        if not (post_consent_turn_count or roleplay or questionnaires or events):
            return
        await self.repository.save_study_record(StudyRecord(
            user_id=user.id,
            participant_id=user.participant_id,
            session_id=session.id,
            consent_version=user.study_consent.version,
            protocol_version=user.study_consent.protocol_version,
            enrolled_at=user.pilot_enrolled_at,
            session_created_at=session.created_at,
            last_activity_at=session.updated_at,
            retention_expires_at=utcnow() + timedelta(days=settings.study_record_retention_days),
            turn_count=post_consent_turn_count,
            scenario_id=roleplay.scenario_id if roleplay else None,
            difficulty=roleplay.difficulty_level if roleplay else None,
            completion_reason=roleplay.completion_reason if roleplay else None,
            feedback_metrics=feedback.metrics if feedback else [],
            feedback_generation_source=feedback.generation_source if feedback else None,
            questionnaires=questionnaires,
            events=events,
            updated_at=utcnow(),
        ))
    async def chat(self, session_id: UUID, user_id: UUID, message: str) -> tuple[ConversationTurn, AgentDecision, Session]:
        session = await self.get_session(session_id, user_id)
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
            content, metadata = CRISIS_RESPONSE, None
            if session.roleplay: session.roleplay.status, session.roleplay.completion_reason = RolePlayStatus.INTERRUPTED, "safety_interruption"
        elif session.roleplay and session.roleplay.status == RolePlayStatus.ACTIVE:
            plan = self.roleplays.plan_response(session.roleplay, message, state)
            roleplay_action = plan.action
            if plan.completed:
                content, metadata = plan.fallback_text, None
                await self.complete_feedback(session)
            elif isinstance(self.generator, OpenAIResponseGenerator):
                content, metadata = await self.generator.generate_roleplay(
                    session,
                    session.roleplay.scenario or SCENARIOS[session.roleplay.scenario_id],
                    plan.action,
                    plan.fallback_text,
                )
            else:
                content, metadata = plan.fallback_text, None
        else: content, metadata = await self.generator.generate(session, message, strategy)
        turn = ConversationTurn(role=Role.ASSISTANT, content=content, strategy=strategy, generation=metadata)
        session.turns.append(turn)
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
        await self.save(session)
        return turn, AgentDecision(emotion_state=state, cognitive_assessment=assessment, strategy=strategy, strategy_scores=strategy_scores, decision_reasons=reasons, analyzer_version=getattr(self.analyzer, "version", "unknown")), session
    async def start_roleplay(self, session_id: UUID, user_id: UUID, scenario_id: str, level: Difficulty, custom=None):
        session = await self.get_session(session_id, user_id)
        state, scenario = self.roleplays.start(scenario_id, level, custom)
        session.roleplay, session.feedback = state, None
        session.title = scenario.title
        session.turns = []
        session.emotion_state = self.analyzer.analyze("")
        turn = ConversationTurn(role=Role.ASSISTANT, content=scenario.opening_line)
        session.turns.append(turn)
        session.research_events.append(ResearchEvent(
            name="roleplay_started",
            properties={"scenario_id": scenario_id, "difficulty": level.value},
        ))
        await self.save(session)
        return state, scenario, turn
    async def set_roleplay_status(self, session_id: UUID, user_id: UUID, action: str):
        session = await self.get_session(session_id, user_id)
        if not session.roleplay: raise ValueError("No role-play")
        if action == "pause" and session.roleplay.status == RolePlayStatus.ACTIVE: session.roleplay.status = RolePlayStatus.PAUSED
        elif action == "resume" and session.roleplay.status == RolePlayStatus.PAUSED: session.roleplay.status = RolePlayStatus.ACTIVE
        elif action == "finish": self.roleplays.finish(session.roleplay); await self.complete_feedback(session)
        else: raise ValueError("Invalid role-play transition")
        session.research_events.append(ResearchEvent(
            name=f"roleplay_{action}",
            properties={"scenario_id": session.roleplay.scenario_id},
        ))
        await self.save(session); return session
    async def rewind_roleplay(self, session_id: UUID, user_id: UUID) -> tuple[str, Session]:
        session = await self.get_session(session_id, user_id)
        state = session.roleplay
        if not state or not state.evidence or len(session.turns) < 3:
            raise ValueError("There is no role-play exchange to rewind")
        if session.turns[-1].role == Role.ASSISTANT:
            session.turns.pop()
        user_turn = session.turns.pop()
        state.evidence.pop()
        state.turn = len(state.evidence)
        state.status = RolePlayStatus.ACTIVE
        state.completion_reason = None
        state.completed_at = None
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
        self, session_id: UUID, user_id: UUID, phase: str, values: dict
    ) -> StudyQuestionnaire:
        if phase not in {"pre", "post"}:
            raise ValueError("Questionnaire phase must be pre or post")
        if not any(value is not None for value in values.values()):
            raise ValueError("At least one rating is required")
        session = await self.get_session(session_id, user_id)
        questionnaire = StudyQuestionnaire(phase=phase, **values)
        session.questionnaires[phase] = questionnaire
        session.research_events.append(ResearchEvent(name=f"questionnaire_{phase}_submitted"))
        await self.save(session)
        return questionnaire
    async def complete_feedback(self, session: Session) -> None:
        if not session.roleplay: return
        feedback = self.roleplays.feedback(session.roleplay)
        previous = next((item for item in await self.repository.list_sessions(session.user_id) if item.id != session.id and item.feedback and item.feedback.scenario_id == session.roleplay.scenario_id), None)
        if previous and previous.feedback:
            old = {metric.name: metric.score for metric in previous.feedback.metrics}
            feedback.compared_with_session_id = previous.id
            feedback.comparisons = [FeedbackComparison(name=metric.name, current_score=metric.score, previous_score=old[metric.name], change=metric.score-old[metric.name]) for metric in feedback.metrics if metric.name in old]
        if isinstance(self.generator, OpenAIResponseGenerator): feedback = await self.generator.phrase_feedback(feedback)
        feedback.session_id = session.id
        session.feedback = feedback
