import math
import re

from app.models.domain import CognitiveAssessment, EmotionLabel, EmotionState, UserIntent
from app.services.interfaces import CognitiveAnalyzer, EmotionAnalyzer

TOKEN_RE = re.compile(r"[a-z']+")
EMOTION_TERMS = {
    EmotionLabel.ANXIETY: {"afraid": 1.0, "anxious": 1.0, "nervous": .8, "scared": 1.0, "worried": .8, "panic": 1.2, "uncertain": .5},
    EmotionLabel.SADNESS: {"sad": 1.0, "down": .6, "hurt": .8, "hopeless": 1.2, "cry": .8, "lonely": .8},
    EmotionLabel.ANGER: {"angry": 1.0, "furious": 1.3, "mad": .8, "hate": 1.0, "unfair": .6},
    EmotionLabel.FRUSTRATION: {"frustrated": 1.0, "annoyed": .7, "stuck": .7, "overloaded": 1.0, "overwhelmed": 1.1, "fight": .8, "fighting": .8, "argument": .8, "conflict": .7},
    EmotionLabel.SHAME: {"ashamed": 1.0, "embarrassed": .8, "incompetent": 1.0, "failure": 1.0, "worthless": 1.2},
    EmotionLabel.GUILT: {"guilty": 1.0, "regret": .8, "sorry": .5, "fault": .7},
    EmotionLabel.JOY: {"happy": 1.0, "excited": 1.0, "glad": .8, "proud": 1.0, "relieved": .8},
}
NEGATIONS = {"not", "never", "hardly", "isn't", "wasn't", "don't", "didn't"}
INTENSIFIERS = {"very": 1.35, "really": 1.25, "extremely": 1.6, "slightly": .65, "somewhat": .75}


class LexicalEmotionAnalyzer(EmotionAnalyzer):
    version = "lexical-v2"

    def analyze(self, text: str) -> EmotionState:
        tokens = TOKEN_RE.findall(text.lower())
        scores = {label: 0.0 for label in EmotionLabel}
        evidence = 0
        for index, token in enumerate(tokens):
            for label, terms in EMOTION_TERMS.items():
                if token not in terms:
                    continue
                weight = terms[token]
                if index and tokens[index - 1] in INTENSIFIERS:
                    weight *= INTENSIFIERS[tokens[index - 1]]
                if any(word in NEGATIONS for word in tokens[max(0, index - 3):index]):
                    weight *= -0.35
                scores[label] += weight
                evidence += 1
        positive = {label: max(score, 0) for label, score in scores.items()}
        raw_total = sum(positive.values())
        neutral_weight = 1.2 if not evidence else .25
        denominator = raw_total + neutral_weight
        distribution = {label: score / denominator for label, score in positive.items()}
        distribution[EmotionLabel.NEUTRAL] += neutral_weight / denominator
        dominant = max(distribution, key=distribution.get)
        confidence = min(.92, .3 + distribution[dominant] * .55 + min(evidence, 3) * .06)
        negative_mass = sum(distribution[label] for label in EmotionLabel if label not in {EmotionLabel.NEUTRAL, EmotionLabel.JOY})
        valence = max(-1, min(1, distribution[EmotionLabel.JOY] * .8 - negative_mass * .75))
        punctuation = min(.15, (text.count("!") + text.count("?")) * .03)
        arousal_labels = {EmotionLabel.ANXIETY, EmotionLabel.ANGER, EmotionLabel.FRUSTRATION, EmotionLabel.JOY}
        arousal = min(1, .2 + sum(distribution[x] for x in arousal_labels) * .75 + punctuation)
        return EmotionState(dominant_emotion=dominant, distribution=distribution, valence=valence, arousal=arousal, intensity=min(1, raw_total / 2.5 + punctuation), confidence=confidence)


RuleBasedEmotionAnalyzer = LexicalEmotionAnalyzer


DISTORTIONS = {
    "mind-reading": (r"\b(?:they|he|she) (?:will|must|probably)(?: definitely)? think\b", r"\bi know (?:they|he|she) think"),
    "catastrophising": (r"\b(?:disaster|catastrophe|ruin everything|worst possible|never recover)\b",),
    "overgeneralisation": (r"\b(?:always|never|everyone|no one|every time)\b",),
    "all-or-nothing thinking": (r"\b(?:completely|total failure|perfect or|nothing works)\b",),
    "should statements": (r"\b(?:i|they|he|she) should\b", r"\bmust always\b"),
    "emotional reasoning": (r"\bi feel .{0,30} so (?:it|that) (?:is|must be)\b",),
    "fortune-telling": (r"\b(?:will definitely|bound to|going to fail|won't work)\b",),
    "personalisation": (r"\b(?:all my fault|because of me|i caused everything)\b",),
    "discounting positives": (r"\b(?:doesn't count|just luck|anyone could)\b",),
    "labelling": (r"\bi(?:'m| am) (?:a )?(?:loser|failure|idiot|bad person)\b",),
}


class RuleBasedCognitiveAnalyzer(CognitiveAnalyzer):
    version = "cognitive-rules-v2"

    def analyze(self, text: str, crisis_detected: bool = False) -> CognitiveAssessment:
        lowered = text.lower()
        scores = {name: min(.9, sum(bool(re.search(pattern, lowered)) for pattern in patterns) * .72) for name, patterns in DISTORTIONS.items()}
        scores = {name: score for name, score in scores.items() if score}
        distortion = max(scores, key=scores.get) if scores else None
        rehearsal = any(term in lowered for term in ("role-play", "roleplay", "practice", "rehearse"))
        practical = any(term in lowered for term in ("how do i", "what should", "help me", "advice", "steps"))
        validation = any(term in lowered for term in ("feel", "upset", "scared", "hurt", "overwhelmed"))
        question = "?" in text
        intent = UserIntent.REHEARSAL if rehearsal else UserIntent.PRACTICAL_HELP if practical else UserIntent.EMOTIONAL_SUPPORT if validation else UserIntent.INFORMATION if question else UserIntent.UNCLEAR
        resistance = .7 if any(term in lowered for term in ("but that won't", "nothing will", "you don't understand", "pointless")) else .15 if "but" in lowered else 0
        readiness = .8 if practical or rehearsal else .65 if question else .35 if validation else .5
        cause_match = re.search(r"\b(?:because|after|when|since)\s+([^.!?]{3,100})", text, re.IGNORECASE)
        cause = cause_match.group(1).strip(" .!?") if cause_match else None
        return CognitiveAssessment(possible_distortion=f"possible {distortion}" if distortion else None, distortion_scores=scores, possible_cause=cause, intent=intent, readiness_for_advice=readiness, resistance=resistance, wants_validation=validation, wants_practical_help=practical, wants_roleplay=rehearsal, confidence=.72 if distortion else .45, crisis_detected=crisis_detected)


def assess_cognition(text: str, crisis_detected: bool) -> CognitiveAssessment:
    return RuleBasedCognitiveAnalyzer().analyze(text, crisis_detected)


class ExponentialStateTracker:
    def __init__(self, alpha: float = .6, trend_threshold: float = .1) -> None:
        self.alpha, self.trend_threshold = alpha, trend_threshold

    def update(self, previous: EmotionState, current: EmotionState) -> EmotionState:
        current.valence = self.alpha * current.valence + (1 - self.alpha) * previous.valence
        old_arousal = previous.arousal
        current.arousal = self.alpha * current.arousal + (1 - self.alpha) * old_arousal
        delta = current.arousal - old_arousal
        current.trend = "increasing" if delta > self.trend_threshold else "decreasing" if delta < -self.trend_threshold else "stable"
        current.resistance = self.alpha * current.resistance + (1 - self.alpha) * previous.resistance
        current.engagement = min(1, previous.engagement + .05)
        current.confidence = 1 / (1 + math.exp(-4 * (current.confidence - .5)))
        return current


def smooth_state(previous: EmotionState, current: EmotionState, alpha: float = .6) -> EmotionState:
    return ExponentialStateTracker(alpha).update(previous, current)
