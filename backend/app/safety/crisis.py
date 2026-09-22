import re

CRISIS_PATTERNS = (
    r"\b(?:(?:want|going|plan|planning|ready|intend|intending) to|might|may) kill myself\b",
    r"\b(?:(?:want|going|plan|planning|ready|intend|intending) to|might|may) end my life\b",
    r"\b(?:take|taking) my own life\b",
    r"\b(?:do not|don't|dont) want to (?:be alive|live|wake up)\b",
    r"\b(?:would be|am) better off dead\b",
    r"\bsuicid(?:e|al)\b",
    r"\b(?:(?:want|going|plan|planning|ready|intend|intending) to|might|may) hurt myself\b",
    r"\bimmediate danger\b",
)

NON_SELF_REPORT_PATTERNS = (
    r"\b(?:not|never) suicidal\b",
    r"\b(?:do not|don't|dont) (?:want|plan|intend) to (?:kill|hurt) myself\b",
    r"\b(?:book|film|article|song|training|questionnaire|headline)\b.{0,40}\b(?:suicide|suicidal|kill myself)\b",
    r"\b(?:he|she|they|my friend|a client|the character) (?:said|says|wrote|asked)\b.{0,50}\b(?:suicide|suicidal|kill myself|end my life)\b",
    r"\b(?:suicide|self-harm) (?:prevention|research|awareness|policy|training)\b",
)


def contains_crisis_language(text: str) -> bool:
    normalized = " ".join(text.split())
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in NON_SELF_REPORT_PATTERNS):
        return False
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in CRISIS_PATTERNS)


CRISIS_RESPONSE = (
    "I’m really sorry you’re facing this. I can’t safely continue normal coaching right now. "
    "If you may act on these thoughts or are in immediate danger, call your local emergency number now "
    "or go to the nearest emergency department. If possible, contact someone you trust and stay with them. "
    "A local crisis line or licensed professional can provide immediate, human support."
)
