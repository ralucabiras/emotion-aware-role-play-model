import re

CRISIS_PATTERNS = (
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bsuicid(?:e|al)\b",
    r"\bhurt myself\b",
    r"\bimmediate danger\b",
)


def contains_crisis_language(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in CRISIS_PATTERNS)


CRISIS_RESPONSE = (
    "I’m really sorry you’re facing this. I can’t safely continue normal coaching right now. "
    "If you may act on these thoughts or are in immediate danger, call your local emergency number now "
    "or go to the nearest emergency department. If possible, contact someone you trust and stay with them. "
    "A local crisis line or licensed professional can provide immediate, human support."
)
