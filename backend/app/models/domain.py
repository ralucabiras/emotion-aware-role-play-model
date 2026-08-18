from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class EmotionLabel(StrEnum):
    ANXIETY = "anxiety"
    SADNESS = "sadness"
    ANGER = "anger"
    FRUSTRATION = "frustration"
    SHAME = "shame"
    GUILT = "guilt"
    JOY = "joy"
    NEUTRAL = "neutral"


class SupportStrategy(StrEnum):
    VALIDATION = "validation"
    REFLECTION = "reflection"
    CLARIFICATION = "clarification"
    VALIDATE_THEN_REFRAME = "validate_then_reframe"
    PRACTICAL_SUGGESTION = "practical_suggestion"
    ROLEPLAY_INVITATION = "roleplay_invitation"
    PAUSE_DEESCALATION = "pause_deescalation"
    SAFETY_ESCALATION = "safety_escalation"


class UserIntent(StrEnum):
    EMOTIONAL_SUPPORT = "emotional_support"
    PRACTICAL_HELP = "practical_help"
    REHEARSAL = "rehearsal"
    INFORMATION = "information"
    UNCLEAR = "unclear"


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class RolePlayStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    DIFFICULT = "difficult"


class EmotionState(BaseModel):
    dominant_emotion: EmotionLabel = EmotionLabel.NEUTRAL
    distribution: dict[EmotionLabel, float] = Field(default_factory=lambda: {EmotionLabel.NEUTRAL: 1.0})
    valence: float = Field(0, ge=-1, le=1)
    arousal: float = Field(0.2, ge=0, le=1)
    intensity: float = Field(0.2, ge=0, le=1)
    confidence: float = Field(0.5, ge=0, le=1)
    trend: str = "stable"
    resistance: float = Field(0, ge=0, le=1)
    engagement: float = Field(0.5, ge=0, le=1)


class CognitiveAssessment(BaseModel):
    possible_distortion: str | None = None
    distortion_scores: dict[str, float] = Field(default_factory=dict)
    possible_cause: str | None = None
    intent: UserIntent = UserIntent.UNCLEAR
    readiness_for_advice: float = Field(0.5, ge=0, le=1)
    resistance: float = Field(0, ge=0, le=1)
    wants_validation: bool = False
    wants_practical_help: bool = False
    wants_roleplay: bool = False
    confidence: float = Field(0.4, ge=0, le=1)
    crisis_detected: bool = False


class GenerationMetadata(BaseModel):
    source: str = "template"
    model: str | None = None
    latency_ms: int | None = None
    fallback_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class ConversationTurn(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    role: Role
    content: str
    created_at: datetime = Field(default_factory=utcnow)
    emotion_state: EmotionState | None = None
    strategy: SupportStrategy | None = None
    generation: GenerationMetadata | None = None


class TurnEvidence(BaseModel):
    turn: int
    concrete_request: bool = False
    excessive_apology: bool = False
    maintained_boundary: bool = False
    blame_language: bool = False
    specific_detail: bool = False
    arousal: float = 0


class RolePlayScenario(BaseModel):
    id: str
    title: str
    character: str
    user_objective: str
    opening_line: str
    expected_skills: list[str]
    difficulty_behaviors: dict[Difficulty, str]
    success_conditions: list[str]
    max_turns: int = 8


class RolePlayState(BaseModel):
    scenario_id: str
    status: RolePlayStatus = RolePlayStatus.ACTIVE
    difficulty_level: Difficulty = Difficulty.BEGINNER
    difficulty: float = Field(0.3, ge=0, le=1)
    cooperation: float = Field(0.7, ge=0, le=1)
    turn: int = 0
    evidence: list[TurnEvidence] = Field(default_factory=list)
    success_progress: float = Field(0, ge=0, le=1)
    completion_reason: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None


class AgentDecision(BaseModel):
    emotion_state: EmotionState
    cognitive_assessment: CognitiveAssessment
    strategy: SupportStrategy
    strategy_scores: dict[SupportStrategy, float] = Field(default_factory=dict)
    decision_reasons: list[str] = Field(default_factory=list)
    analyzer_version: str = "lexical-v2"


class FeedbackMetric(BaseModel):
    name: str
    score: float = Field(ge=0, le=1)
    evidence_turns: list[int] = Field(default_factory=list)


class SessionFeedback(BaseModel):
    session_id: UUID | None = None
    scenario_id: str
    metrics: list[FeedbackMetric]
    observed: list[str]
    strengths: list[str]
    suggestions: list[str]
    generation_source: str = "deterministic"
    created_at: datetime = Field(default_factory=utcnow)


class StudyQuestionnaire(BaseModel):
    phase: str
    confidence: int | None = Field(default=None, ge=1, le=7)
    anxiety: int | None = Field(default=None, ge=1, le=7)
    realism: int | None = Field(default=None, ge=1, le=7)
    usefulness: int | None = Field(default=None, ge=1, le=7)
    submitted_at: datetime = Field(default_factory=utcnow)


class ResearchEvent(BaseModel):
    name: str
    created_at: datetime = Field(default_factory=utcnow)
    properties: dict[str, str | int | float | bool] = Field(default_factory=dict)


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    email: str
    password_hash: str
    consented_at: datetime
    participant_id: UUID = Field(default_factory=uuid4)
    consent_version: str = "legacy-privacy-v1"
    first_name: str = ""
    last_name: str = ""
    preferred_name: str = ""
    country: str = ""
    timezone: str = "UTC"
    email_verified_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Session(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field(default_factory=lambda: utcnow() + timedelta(days=30))
    turns: list[ConversationTurn] = Field(default_factory=list)
    emotion_state: EmotionState = Field(default_factory=EmotionState)
    roleplay: RolePlayState | None = None
    feedback: SessionFeedback | None = None
    questionnaires: dict[str, StudyQuestionnaire] = Field(default_factory=dict)
    research_events: list[ResearchEvent] = Field(default_factory=list)
