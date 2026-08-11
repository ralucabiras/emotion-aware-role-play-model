from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.domain import (
    AgentDecision,
    ConversationTurn,
    Difficulty,
    EmotionState,
    RolePlayScenario,
    RolePlayState,
    SessionFeedback,
)


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    consent: bool = False
class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"
class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
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
    feedback: SessionFeedback | None = None
class SessionResponse(BaseModel):
    session_id: UUID
    turns: list[ConversationTurn]
    emotion_state: EmotionState
    roleplay: RolePlayState | None = None
    feedback: SessionFeedback | None = None
class SessionSummary(BaseModel):
    session_id: UUID
    updated_at: str
    turn_count: int
    roleplay: RolePlayState | None = None
class StartRolePlayRequest(BaseModel):
    scenario_id: str
    difficulty: Difficulty = Difficulty.BEGINNER
class StartRolePlayResponse(BaseModel):
    state: RolePlayState
    scenario: RolePlayScenario
    opening_turn: ConversationTurn
class RolePlayActionRequest(BaseModel):
    action: str


class MultimodalAffectRequest(BaseModel):
    session_id: UUID
    message: str = Field(min_length=1, max_length=5000)
    audio_wav_base64: str = Field(min_length=1, max_length=7_000_000)


class MultimodalAffectResponse(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    distribution: dict[str, float]
    model_version: str
    audio_persisted: bool = False
    disclaimer: str = "Research estimate; uncertain and not a diagnosis."
