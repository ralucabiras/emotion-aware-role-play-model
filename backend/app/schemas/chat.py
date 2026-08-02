from uuid import UUID

from pydantic import BaseModel, Field

from app.models.domain import AgentDecision, ConversationTurn, EmotionState, RolePlayScenario, RolePlayState


class CreateSessionResponse(BaseModel):
    session_id: UUID
    emotion_state: EmotionState


class ChatRequest(BaseModel):
    session_id: UUID
    message: str = Field(min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    turn: ConversationTurn
    decision: AgentDecision
    roleplay: RolePlayState | None = None


class SessionResponse(BaseModel):
    session_id: UUID
    turns: list[ConversationTurn]
    emotion_state: EmotionState
    roleplay: RolePlayState | None = None


class StartRolePlayRequest(BaseModel):
    scenario_id: str


class StartRolePlayResponse(BaseModel):
    state: RolePlayState
    scenario: RolePlayScenario
    opening_turn: ConversationTurn

