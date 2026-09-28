from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, model_validator

from app.models.domain import (
    ActionCard,
    AgentDecision,
    BranchLineage,
    ConversationTurn,
    Difficulty,
    EmotionState,
    MultimodalEstimate,
    PracticeGoal,
    PreparationDetails,
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
    researcher: bool = False
    pilot_enrolled: bool = False
    study_consent_version: str | None = None
    study_consented_at: str | None = None
    eligibility_version: str | None = None
    eligibility_confirmed_at: str | None = None
    study_withdrawn: bool = False
    study_withdrawn_at: str | None = None
    participant_id: UUID


class OnboardingRequest(BaseModel):
    practice_goals: list[PracticeGoal] = Field(min_length=1, max_length=3)


class PilotEnrollmentRequest(BaseModel):
    access_code: str = Field(min_length=1, max_length=100)
    consent_version: str = Field(min_length=1, max_length=80)
    eligibility_version: str = Field(min_length=1, max_length=80)
    age_confirmed: StrictBool = False
    geography_confirmed: StrictBool = False
    english_confirmed: StrictBool = False
    other_criteria_confirmed: StrictBool = False
    information_sheet_read: bool = False
    research_participation_accepted: bool = False
    data_processing_accepted: bool = False


class StudyContact(BaseModel):
    name: str
    email: str


class StudyInformationResponse(BaseModel):
    eligibility_version: str
    minimum_participant_age: int
    geographic_scope: str
    supported_language: str
    other_eligibility_criteria: list[str]
    version: str
    protocol_version: str
    study_label: str
    title: str
    summary: str
    data_collected: list[str]
    processors: list[str]
    audio_and_transcripts: list[str]
    retention: str
    risks_and_limitations: list[str]
    withdrawal: list[str]
    researcher: StudyContact
    supervisor: StudyContact
    institution: str


class StudyWithdrawalRequest(BaseModel):
    confirm_withdrawal: bool = False


class StudyWithdrawalResponse(BaseModel):
    user: UserResponse
    questionnaires_deleted: int
    research_events_deleted: int
    message: str
    anonymized_analysis_notice: str


class StudyLifecycleUpdateRequest(BaseModel):
    start_date: date
    end_date: date


class ParticipantResearchUpdateRequest(BaseModel):
    excluded: bool
    exclusion_reason: str = Field(default="", max_length=300)
    data_quality_notes: str = Field(default="", max_length=500)


class DatasetFreezeRequest(BaseModel):
    confirm_freeze: bool = False


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
    version: int = 0
    session_id: UUID
    emotion_state: EmotionState
class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID | None = None
    expected_version: int | None = Field(default=None, ge=0)
    audio_wav_base64: str | None = Field(default=None, min_length=1, max_length=7_000_000)
    adaptation_enabled: StrictBool = False
    pacing: Literal["auto", "keep_going", "gentler", "more_challenge"] = "auto"

    @model_validator(mode="after")
    def require_exchange_binding(self):
        enhanced = self.audio_wav_base64 is not None or self.adaptation_enabled or self.pacing != "auto"
        if enhanced or self.request_id is not None or self.expected_version is not None:
            if self.request_id is None or self.expected_version is None:
                raise ValueError("A request ID and expected session version are required")
        return self

    session_id: UUID
    message: str = Field(min_length=1, max_length=5000)
class ChatResponse(BaseModel):
    user_turn: ConversationTurn | None = None
    version: int = 0
    turn: ConversationTurn
    decision: AgentDecision
    roleplay: RolePlayState | None = None
    feedback: SessionFeedback | None = None
    post_questionnaire_token: str | None = None
class SessionResponse(BaseModel):
    branch: BranchLineage | None = None
    version: int = 0
    questionnaires: dict[str, StudyQuestionnaire] = Field(default_factory=dict)
    questionnaire_skips: dict[str, str] = Field(default_factory=dict)
    session_id: UUID
    title: str
    turns: list[ConversationTurn]
    emotion_state: EmotionState
    roleplay: RolePlayState | None = None
    feedback: SessionFeedback | None = None
    post_questionnaire_token: str | None = None
    takeaway: str = ""
class SessionSummary(BaseModel):
    version: int = 0
    session_id: UUID
    title: str
    created_at: str
    updated_at: str
    turn_count: int
    roleplay: RolePlayState | None = None
    feedback: SessionFeedback | None = None
    takeaway: str = ""


class SessionTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class TakeawayRequest(BaseModel):
    takeaway: str = Field(max_length=500)


class StudyQuestionnaireRequest(BaseModel):
    skipped: StrictBool = False
    post_token: str | None = Field(default=None, max_length=100)
    confidence: int | None = Field(default=None, ge=1, le=7)
    anxiety: int | None = Field(default=None, ge=1, le=7)
    realism: int | None = Field(default=None, ge=1, le=7)
    usefulness: int | None = Field(default=None, ge=1, le=7)


class StudyQuestionnaireResponse(BaseModel):
    questionnaire: StudyQuestionnaire | None
class PreRehearsalRatings(BaseModel):
    confidence: int = Field(ge=1, le=7)
    anxiety: int = Field(ge=1, le=7)


class StartRolePlayRequest(BaseModel):
    character_profile: Literal["cooperative", "rushed", "sceptical"] | None = None
    attempt_purpose: Literal["required", "additional", "retry"] = "additional"
    required_task_id: Literal["workload", "boundary", "relationship"] | None = None
    scenario_id: str
    difficulty: Difficulty = Difficulty.BEGINNER
    pre_ratings: PreRehearsalRatings | None = None
    pre_skipped: StrictBool = False
class StartRolePlayResponse(BaseModel):
    version: int = 0
    session_id: UUID
    emotion_state: EmotionState
    state: RolePlayState
    scenario: RolePlayScenario
    opening_turn: ConversationTurn
class RolePlayActionRequest(BaseModel):
    action: str


class CustomScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    preparation: PreparationDetails | None = None
    title: str = Field(min_length=3, max_length=80)
    character: str = Field(min_length=2, max_length=50)
    situation: str = Field(min_length=10, max_length=500)
    user_objective: str = Field(min_length=10, max_length=300)
    opening_line: str = Field(min_length=3, max_length=300)
    skills: list[str] = Field(min_length=1, max_length=3)


class RewindResponse(BaseModel):
    removed_message: str
    session: SessionResponse


class MultimodalAffectRequest(BaseModel):
    session_id: UUID
    message: str = Field(min_length=1, max_length=5000)
    audio_wav_base64: str = Field(min_length=1, max_length=7_000_000)


class MultimodalAffectResponse(MultimodalEstimate):
    pass


class AudioTranscriptionRequest(BaseModel):
    audio_wav_base64: str = Field(min_length=1, max_length=7_000_000)


class AudioTranscriptionResponse(BaseModel):
    text: str
    model: str
    latency_ms: int
    audio_persisted: bool = False


class BranchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turn_id: UUID
    expected_version: int = Field(ge=0)
    request_id: UUID


class PreparationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    who: str = Field(min_length=2, max_length=50)
    happened: str = Field(min_length=10, max_length=500)
    desired_outcome: str = Field(min_length=10, max_length=300)
    difficult_part: str = Field(min_length=1, max_length=500)


class ActionCardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(ge=0)
    opening_sentence: str = Field(min_length=1, max_length=500)
    main_request: str = Field(min_length=1, max_length=500)
    boundary_or_fallback: str = Field(min_length=1, max_length=500)
    reminder: str = Field(min_length=1, max_length=300)


class ActionCardResponse(BaseModel):
    version: int
    card: ActionCard
    saved: bool
