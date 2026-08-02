from app.models.domain import CognitiveAssessment, EmotionState, SupportStrategy
from app.services.interfaces import StrategySelector


class RuleBasedStrategySelector(StrategySelector):
    def select(self, state: EmotionState, assessment: CognitiveAssessment) -> SupportStrategy:
        if assessment.crisis_detected:
            return SupportStrategy.SAFETY_ESCALATION
        if state.arousal > 0.82:
            return SupportStrategy.PAUSE_DEESCALATION
        if assessment.wants_roleplay:
            return SupportStrategy.ROLEPLAY_INVITATION
        if assessment.possible_distortion:
            return SupportStrategy.VALIDATE_THEN_REFRAME
        if assessment.wants_practical_help:
            return SupportStrategy.PRACTICAL_SUGGESTION
        return SupportStrategy.VALIDATION

