import re

from app.models.domain import CognitiveAssessment, EmotionLabel, EmotionState
from app.services.interfaces import EmotionAnalyzer

KEYWORDS = {
    EmotionLabel.ANXIETY: {"afraid", "anxious", "nervous", "scared", "worried", "panic"},
    EmotionLabel.SADNESS: {"sad", "down", "hurt", "hopeless", "cry"},
    EmotionLabel.ANGER: {"angry", "furious", "mad", "hate"},
    EmotionLabel.FRUSTRATION: {"frustrated", "annoyed", "stuck", "overloaded", "overwhelmed"},
    EmotionLabel.SHAME: {"ashamed", "embarrassed", "incompetent", "failure"},
    EmotionLabel.GUILT: {"guilty", "regret", "sorry"},
    EmotionLabel.JOY: {"happy", "excited", "glad", "proud"},
}


class RuleBasedEmotionAnalyzer(EmotionAnalyzer):
    def analyze(self, text: str) -> EmotionState:
        words = set(re.findall(r"[a-z']+", text.lower()))
        scores = {label: len(words & terms) for label, terms in KEYWORDS.items()}
        dominant, hits = max(scores.items(), key=lambda item: item[1])
        if hits == 0:
            dominant = EmotionLabel.NEUTRAL
        negative = dominant not in {EmotionLabel.NEUTRAL, EmotionLabel.JOY}
        intensity = min(0.35 + hits * 0.18 + text.count("!") * 0.05, 1)
        confidence = min(0.45 + hits * 0.12, 0.88) if hits else 0.35
        distribution = {label: 0.0 for label in EmotionLabel}
        distribution[dominant] = confidence
        distribution[EmotionLabel.NEUTRAL] += 1 - confidence
        return EmotionState(
            dominant_emotion=dominant,
            distribution=distribution,
            valence=(-0.6 if negative else 0.55 if dominant == EmotionLabel.JOY else 0),
            arousal=min(0.35 + hits * 0.15, 0.9),
            intensity=intensity,
            confidence=confidence,
        )


def assess_cognition(text: str, crisis_detected: bool) -> CognitiveAssessment:
    lowered = text.lower()
    distortion = None
    if any(term in lowered for term in ("will think", "they think", "must think")):
        distortion = "possible mind-reading"
    elif any(term in lowered for term in ("disaster", "ruin everything", "worst", "never recover")):
        distortion = "possible catastrophising"
    elif any(term in lowered for term in ("always", "never", "everyone", "no one")):
        distortion = "possible overgeneralisation"
    return CognitiveAssessment(
        possible_distortion=distortion,
        wants_practical_help=any(term in lowered for term in ("how do i", "what should", "help me")),
        wants_roleplay=any(term in lowered for term in ("role-play", "roleplay", "practice", "rehearse")),
        wants_validation=any(term in lowered for term in ("feel", "upset", "scared", "hurt")),
        confidence=0.65 if distortion else 0.4,
        crisis_detected=crisis_detected,
    )


def smooth_state(previous: EmotionState, current: EmotionState, alpha: float = 0.6) -> EmotionState:
    valence = alpha * current.valence + (1 - alpha) * previous.valence
    arousal = alpha * current.arousal + (1 - alpha) * previous.arousal
    delta = arousal - previous.arousal
    current.valence, current.arousal = valence, arousal
    current.trend = "increasing" if delta > 0.12 else "decreasing" if delta < -0.12 else "stable"
    current.engagement = min(1, previous.engagement + 0.05)
    return current

