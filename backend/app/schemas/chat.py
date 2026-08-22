from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.domain import (
    AgentDecision,
    ConversationTurn,
    Difficulty,
    EmotionState,
    PracticeGoal,
    RolePlayScenario,
    RolePlayState,
    SessionFeedback,
    StudyQuestionnaire,
)


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    consent: bool = False
    first_name: str = Field(default="", max_length=80)
    last_name: str = Field(default="", max_length=80)
    preferred_name: str = Field(default="", max_length=80)
    country: str = Field(default="", max_length=80)
    timezone: str = Field(default="UTC", max_length=80)
class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"
class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    preferred_name: str = ""
    country: str = ""
    timezone: str = "UTC"
    email_verified: bool = False
    practice_goals: list[PracticeGoal] = Field(default_factory=list)
    onboarding_completed: bool = False
    onboarding_version: str | None = None


class OnboardingRequest(BaseModel):
    practice_goals: list[PracticeGoal] = Field(min_length=1, max_length=3)


class ProfileUpdateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    preferred_name: str = Field(default="", max_length=80)
    country: str = Field(default="", max_length=80)
    timezone: str = Field(min_length=1, max_length=80)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=10, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=10, max_length=128)


class RegistrationResponse(BaseModel):
    message: str
    email: EmailStr


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class ResendVerificationRequest(BaseModel):
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
    title: str
    turns: list[ConversationTurn]
    emotion_state: EmotionState
    roleplay: RolePlayState | None = None
    feedback: SessionFeedback | None = None
class SessionSummary(BaseModel):
    session_id: UUID
    title: str
    created_at: str
    updated_at: str
    turn_count: int
    roleplay: RolePlayState | None = None
    feedback: SessionFeedback | None = None


class SessionTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class StudyQuestionnaireRequest(BaseModel):
    confidence: int | None = Field(default=None, ge=1, le=7)
    anxiety: int | None = Field(default=None, ge=1, le=7)
    realism: int | None = Field(default=None, ge=1, le=7)
    usefulness: int | None = Field(default=None, ge=1, le=7)


class StudyQuestionnaireResponse(BaseModel):
    questionnaire: StudyQuestionnaire
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
    text_label: str
    text_confidence: float = Field(ge=0, le=1)
    text_distribution: dict[str, float]
    audio_label: str
    audio_confidence: float = Field(ge=0, le=1)
    audio_distribution: dict[str, float]
    modalities_agree: bool
    confidence_level: str
    low_confidence_threshold: float = Field(ge=0, le=1)
    model_version: str
    latency_ms: int
    queue_ms: int = 0
    audio_persisted: bool = False
    disclaimer: str = "Research estimate; uncertain and not a diagnosis."


class AudioTranscriptionRequest(BaseModel):
    audio_wav_base64: str = Field(min_length=1, max_length=7_000_000)


class AudioTranscriptionResponse(BaseModel):
    text: str
    model: str
    latency_ms: int
    audio_persisted: bool = False
