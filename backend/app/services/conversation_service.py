from uuid import UUID

from app.models.domain import AgentDecision, ConversationTurn, Role, Session
from app.safety.crisis import CRISIS_RESPONSE, contains_crisis_language
from app.services.affect_service import RuleBasedEmotionAnalyzer, assess_cognition, smooth_state
from app.services.interfaces import EmotionAnalyzer, ResponseGenerator, StrategySelector
from app.services.llm_service import TemplateResponseGenerator
from app.services.roleplay_service import RolePlayService
from app.services.strategy_service import RuleBasedStrategySelector


class SessionNotFoundError(KeyError):
    pass


class ConversationService:
    def __init__(
        self,
        analyzer: EmotionAnalyzer | None = None,
        selector: StrategySelector | None = None,
        generator: ResponseGenerator | None = None,
    ) -> None:
        self.sessions: dict[UUID, Session] = {}
        self.analyzer = analyzer or RuleBasedEmotionAnalyzer()
        self.selector = selector or RuleBasedStrategySelector()
        self.generator = generator or TemplateResponseGenerator()
        self.roleplays = RolePlayService()

    def create_session(self) -> Session:
        session = Session()
        self.sessions[session.id] = session
        return session

    def get_session(self, session_id: UUID) -> Session:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise SessionNotFoundError from exc

    def delete_session(self, session_id: UUID) -> None:
        if self.sessions.pop(session_id, None) is None:
            raise SessionNotFoundError

    async def chat(self, session_id: UUID, message: str) -> tuple[ConversationTurn, AgentDecision]:
        session = self.get_session(session_id)
        crisis = contains_crisis_language(message)
        state = smooth_state(session.emotion_state, self.analyzer.analyze(message))
        assessment = assess_cognition(message, crisis)
        strategy = self.selector.select(state, assessment)
        session.emotion_state = state
        session.turns.append(ConversationTurn(role=Role.USER, content=message, emotion_state=state))

        if crisis:
            content = CRISIS_RESPONSE
        elif session.roleplay and session.roleplay.active:
            content = self.roleplays.respond(session.roleplay, message, state)
        else:
            content = await self.generator.generate(session, message, strategy)
        turn = ConversationTurn(role=Role.ASSISTANT, content=content, strategy=strategy)
        session.turns.append(turn)
        return turn, AgentDecision(emotion_state=state, cognitive_assessment=assessment, strategy=strategy)


conversation_service = ConversationService()
