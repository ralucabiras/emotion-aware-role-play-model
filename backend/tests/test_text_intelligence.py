from app.models.domain import EmotionLabel, EmotionState, SupportStrategy, UserIntent
from app.services.affect_service import (
    ExponentialStateTracker,
    LexicalEmotionAnalyzer,
    RuleBasedCognitiveAnalyzer,
)
from app.services.strategy_service import ScoredStrategySelector


def test_emotion_distribution_negation_and_intensity() -> None:
    analyzer = LexicalEmotionAnalyzer()
    anxious = analyzer.analyze("I am extremely scared and very worried!")
    negated = analyzer.analyze("I am not scared")
    assert anxious.dominant_emotion == EmotionLabel.ANXIETY
    assert abs(sum(anxious.distribution.values()) - 1) < 1e-9
    assert anxious.intensity > negated.intensity
    assert anxious.arousal > negated.arousal


def test_cognition_intent_distortion_cause_and_resistance() -> None:
    analyzer = RuleBasedCognitiveAnalyzer()
    result = analyzer.analyze("They will definitely think I am a failure because I missed one deadline. What should I do?")
    assert result.possible_distortion
    assert result.intent == UserIntent.PRACTICAL_HELP
    assert result.possible_cause == "I missed one deadline"
    resistant = analyzer.analyze("But that won't work. This is pointless.")
    assert resistant.resistance > .5


def test_state_tracker_smooths_and_tracks_trend() -> None:
    tracker = ExponentialStateTracker(alpha=.5, trend_threshold=.1)
    state = tracker.update(EmotionState(arousal=.2), EmotionState(arousal=.8, valence=-.8))
    assert state.arousal == .5
    assert state.valence == -.4
    assert state.trend == "increasing"


def test_strategy_policy_is_scored_and_safety_wins() -> None:
    cognition = RuleBasedCognitiveAnalyzer().analyze("How do I handle this?", crisis_detected=False)
    decision = ScoredStrategySelector().decide(EmotionState(), cognition)
    assert decision.strategy == SupportStrategy.PRACTICAL_SUGGESTION
    assert decision.scores[decision.strategy] > 0
    crisis = RuleBasedCognitiveAnalyzer().analyze("anything", crisis_detected=True)
    assert ScoredStrategySelector().decide(EmotionState(arousal=1), crisis).strategy == SupportStrategy.SAFETY_ESCALATION

