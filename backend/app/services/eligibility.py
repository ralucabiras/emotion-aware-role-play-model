"""Versioned self-attestation; never collect reasons for ineligibility."""
import hashlib
import json

from app.core.config import settings

OTHER_CRITERIA = [
    "I can understand the participant information and provide informed consent.",
    "I have access to a compatible web browser and can complete the study independently.",
    "I am willing to rehearse ordinary interpersonal conversations and complete all three standardized tasks.",
    "I am not seeking diagnosis, treatment, crisis care, or emergency support from AffectLab.",
    "I am not currently in an acute crisis or experiencing an immediate risk requiring emergency or clinical support.",
    "I have not previously participated under another account.",
    "I am not a research-team member directly involved in developing or assessing AffectLab.",
]


def eligibility_version() -> str:
    criteria = [settings.study_protocol_version, settings.minimum_participant_age,
                settings.geographic_scope, settings.supported_language, OTHER_CRITERIA]
    digest = hashlib.sha256(json.dumps(criteria, ensure_ascii=True).encode()).hexdigest()[:16]
    return f"eligibility-v1-{digest}"


def has_current_eligibility(user) -> bool:
    return bool(user.study_eligibility and user.study_eligibility.version == eligibility_version()
                and user.study_eligibility.protocol_version == settings.study_protocol_version)
