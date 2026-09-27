"""Stored application decisions, not inferred psychology or model reasoning."""
from app.models.domain import AffectDecision

SUPPORTED = {"anger", "happiness", "neutral", "sadness"}
WORDING = {
    "baseline": "",
    "acknowledge": "I hear you. ",
    "offer_pacing": "Would you prefer to keep going, take a gentler pace, or add more challenge? ",
    "gentler": "Take your time. We can work through one point at a time. ",
    "more_challenge": "Be specific about what you can commit to as you respond. ",
}


def select(record: AffectDecision, eligible: bool, ended: bool = False, crisis: bool = False) -> str:
    if crisis or ended or not eligible:
        record.reason = "safety_override" if crisis else "rehearsal_ended" if ended else "baseline_session"
    elif record.preference != "auto":
        record.action = "baseline" if record.preference == "keep_going" else record.preference
        record.reason = "user_preference"
    elif not record.adaptation_enabled:
        record.reason = "adaptation_disabled"
    elif record.prediction is None:
        record.reason = record.fallback_reason or "missing_audio"
    else:
        p = record.prediction
        if any(label not in SUPPORTED for values in (p.distribution, p.text_distribution, p.audio_distribution) for label in values):
            record.reason = "unsupported_categories"
        elif min(p.confidence, p.text_confidence, p.audio_confidence) < p.low_confidence_threshold:
            record.action, record.reason = "offer_pacing", "low_confidence"
        elif not p.modalities_agree or p.label != p.text_label:
            record.action, record.reason = "offer_pacing", "modality_disagreement"
        elif p.label in {"anger", "sadness"}:
            record.action, record.reason = "acknowledge", "supported_matching_estimates"
        else:
            record.reason = "no_adaptation_for_label"
    return WORDING[record.action]
