import pytest

from app.safety.crisis import contains_crisis_language


@pytest.mark.parametrize("text", [
    "I want to kill myself.",
    "I am planning to end my life tonight.",
    "I might take my own life.",
    "I don't want to be alive anymore.",
    "I would be better off dead.",
    "I am suicidal.",
    "I may hurt myself.",
])
def test_crisis_paraphrases_trigger_safety_response(text):
    assert contains_crisis_language(text)


@pytest.mark.parametrize("text", [
    "I am not suicidal.",
    "I don't want to kill myself; I want help with the anxiety.",
    "My friend said she wants to kill herself.",
    "The character says 'I plan to end my life' in the film.",
    "I am writing an article about suicide prevention.",
    "Our workplace has self-harm awareness training.",
    "This deadline is killing me.",
    "I could die of embarrassment.",
])
def test_negation_quotation_and_false_positive_cases_do_not_trigger(text):
    assert not contains_crisis_language(text)


@pytest.mark.parametrize("text", [
    "I cannot go on like this.",
    "I want everything to stop.",
    "There is no point anymore.",
])
def test_ambiguous_distress_is_not_claimed_as_crisis_by_lexical_detector(text):
    assert not contains_crisis_language(text)
