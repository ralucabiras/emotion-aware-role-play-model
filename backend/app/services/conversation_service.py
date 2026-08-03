from datetime import timedelta
from uuid import UUID

from app.core.config import settings
from app.models.domain import (
    AgentDecision,
    ConversationTurn,
    Difficulty,
    Role,
    RolePlayStatus,
    Session,
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
from app.services.roleplay_service import RolePlayService
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
        return await self.repository.save_session(Session(user_id=user_id))
    async def get_session(self, session_id: UUID, user_id: UUID) -> Session:
        session = await self.repository.get_session(session_id, user_id)
        if not session: raise SessionNotFoundError
        return session
    async def list_sessions(self, user_id: UUID) -> list[Session]: return await self.repository.list_sessions(user_id)
    async def delete_session(self, session_id: UUID, user_id: UUID) -> None:
        if not await self.repository.delete_session(session_id, user_id): raise SessionNotFoundError
    async def save(self, session: Session) -> None:
        session.updated_at, session.expires_at = utcnow(), utcnow() + timedelta(days=settings.session_retention_days)
        await self.repository.save_session(session)
    async def chat(self, session_id: UUID, user_id: UUID, message: str) -> tuple[ConversationTurn, AgentDecision, Session]:
        session = await self.get_session(session_id, user_id)
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
        if crisis:
            content, metadata = CRISIS_RESPONSE, None
            if session.roleplay: session.roleplay.status, session.roleplay.completion_reason = RolePlayStatus.INTERRUPTED, "safety_interruption"
        elif session.roleplay and session.roleplay.status == RolePlayStatus.ACTIVE:
            content, metadata = self.roleplays.respond(session.roleplay, message, state), None
            if session.roleplay.status == RolePlayStatus.COMPLETED: await self.complete_feedback(session)
        else: content, metadata = await self.generator.generate(session, message, strategy)
        turn = ConversationTurn(role=Role.ASSISTANT, content=content, strategy=strategy, generation=metadata)
        session.turns.append(turn)
        await self.save(session)
        return turn, AgentDecision(emotion_state=state, cognitive_assessment=assessment, strategy=strategy, strategy_scores=strategy_scores, decision_reasons=reasons, analyzer_version=getattr(self.analyzer, "version", "unknown")), session
    async def start_roleplay(self, session_id: UUID, user_id: UUID, scenario_id: str, level: Difficulty):
        session = await self.get_session(session_id, user_id)
        state, scenario = self.roleplays.start(scenario_id, level)
        session.roleplay, session.feedback = state, None
        turn = ConversationTurn(role=Role.ASSISTANT, content=scenario.opening_line)
        session.turns.append(turn); await self.save(session)
        return state, scenario, turn
    async def set_roleplay_status(self, session_id: UUID, user_id: UUID, action: str):
        session = await self.get_session(session_id, user_id)
        if not session.roleplay: raise ValueError("No role-play")
        if action == "pause" and session.roleplay.status == RolePlayStatus.ACTIVE: session.roleplay.status = RolePlayStatus.PAUSED
        elif action == "resume" and session.roleplay.status == RolePlayStatus.PAUSED: session.roleplay.status = RolePlayStatus.ACTIVE
        elif action == "finish": self.roleplays.finish(session.roleplay); await self.complete_feedback(session)
        else: raise ValueError("Invalid role-play transition")
        await self.save(session); return session
    async def complete_feedback(self, session: Session) -> None:
        if not session.roleplay: return
        feedback = self.roleplays.feedback(session.roleplay)
        if isinstance(self.generator, OpenAIResponseGenerator): feedback = await self.generator.phrase_feedback(feedback)
        session.feedback = feedback
