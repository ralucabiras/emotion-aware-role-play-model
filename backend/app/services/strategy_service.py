from dataclasses import dataclass

from app.models.domain import CognitiveAssessment, EmotionState, SupportStrategy, UserIntent
from app.services.interfaces import StrategySelector


@dataclass
class StrategyDecision:
    strategy: SupportStrategy
    scores: dict[SupportStrategy, float]
    reasons: list[str]


class ScoredStrategySelector(StrategySelector):
    """Auditable baseline policy whose scores can be evaluated independently."""

    def decide(self, state: EmotionState, assessment: CognitiveAssessment) -> StrategyDecision:
        scores = {strategy: .05 for strategy in SupportStrategy}
        reasons: list[str] = []
        if assessment.crisis_detected:
            scores[SupportStrategy.SAFETY_ESCALATION] = 1
            return StrategyDecision(SupportStrategy.SAFETY_ESCALATION, scores, ["crisis language detected"])
        if state.arousal > .8:
            scores[SupportStrategy.PAUSE_DEESCALATION] += .9
            reasons.append("high arousal estimate")
        if assessment.intent == UserIntent.REHEARSAL:
            scores[SupportStrategy.ROLEPLAY_INVITATION] += .85
            reasons.append("explicit rehearsal intent")
        if assessment.possible_distortion and assessment.confidence >= .6:
            scores[SupportStrategy.VALIDATE_THEN_REFRAME] += .9
            scores[SupportStrategy.VALIDATION] += .25
            reasons.append("tentative cognitive pattern")
        if assessment.intent == UserIntent.PRACTICAL_HELP and assessment.readiness_for_advice >= .6:
            scores[SupportStrategy.PRACTICAL_SUGGESTION] += .7
            reasons.append("practical-help intent and advice readiness")
        if assessment.wants_validation or state.valence < -.4:
            scores[SupportStrategy.VALIDATION] += .55
            reasons.append("validation signal or negative valence")
        if assessment.resistance > .5:
            scores[SupportStrategy.REFLECTION] += .65
            scores[SupportStrategy.PRACTICAL_SUGGESTION] -= .3
            reasons.append("resistance signal favors reflection")
        if assessment.intent == UserIntent.UNCLEAR:
            scores[SupportStrategy.CLARIFICATION] += .45
            reasons.append("unclear intent")
        strategy = max(scores, key=scores.get)
        return StrategyDecision(strategy, scores, reasons or ["default supportive baseline"])

    def select(self, state: EmotionState, assessment: CognitiveAssessment) -> SupportStrategy:
        return self.decide(state, assessment).strategy


RuleBasedStrategySelector = ScoredStrategySelector
