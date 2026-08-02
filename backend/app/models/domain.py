from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


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


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


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
    possible_cause: str | None = None
    wants_validation: bool = False
    wants_practical_help: bool = False
    wants_roleplay: bool = False
    confidence: float = Field(0.4, ge=0, le=1)
    crisis_detected: bool = False


class ConversationTurn(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    role: Role
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    emotion_state: EmotionState | None = None
    strategy: SupportStrategy | None = None


class RolePlayScenario(BaseModel):
    id: str
    title: str
    character: str
    user_objective: str
    opening_line: str
    expected_skills: list[str]


class RolePlayState(BaseModel):
    scenario_id: str
    active: bool = True
    difficulty: float = Field(0.3, ge=0, le=1)
    cooperation: float = Field(0.7, ge=0, le=1)
    turn: int = 0


class AgentDecision(BaseModel):
    emotion_state: EmotionState
    cognitive_assessment: CognitiveAssessment
    strategy: SupportStrategy


class SessionFeedback(BaseModel):
    strengths: list[str]
    suggestions: list[str]
    observed: list[str]


class Session(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    turns: list[ConversationTurn] = Field(default_factory=list)
    emotion_state: EmotionState = Field(default_factory=EmotionState)
    roleplay: RolePlayState | None = None
