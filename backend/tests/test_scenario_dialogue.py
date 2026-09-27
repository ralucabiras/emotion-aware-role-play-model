"""Synthetic engineering cases for profiled practice; not participant evidence."""
from uuid import uuid4

import pytest

from app.models.domain import Difficulty, EmotionState, RolePlayState, Session
from app.repositories.memory import MemoryRepository
from app.schemas.chat import StartRolePlayRequest
from app.services.conversation_service import ConversationService
from app.services.llm_service import TemplateResponseGenerator
from app.services.roleplay_service import RolePlayService
from app.services.scenario_dialogue import DEFINITIONS, PROFILES, VERSION, features

OPENING = "When we spend evenings apart, I feel lonely and I need time together."
REQUEST = "I understand you are tired. Could we talk for 20 minutes on Saturday as a trial and review it on Sunday?"
REFUSAL = "I cannot take this on."
CLOSE = "My answer is still no. Thank you for understanding."


async def start(scenario, profile="cooperative", level=Difficulty.INTERMEDIATE):
    service = ConversationService(MemoryRepository(), generator=TemplateResponseGenerator())
    session = await service.create_session(uuid4())
    session, _, _ = await service.start_roleplay(session.id, session.user_id, scenario, level,
        pre_skipped=True, character_profile=profile)
    return service, session


async def say(service, session, message):
    return (await service.chat(session.id, session.user_id, message))[2]


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("level", list(Difficulty))
async def test_boundary_without_compromise(profile, level):
    service, session = await start("boundary", profile, level)
    await say(service, session, REFUSAL)
    assert session.roleplay.dialogue.stage == "pressure"
    assert not session.feedback
    count = (2 if level == Difficulty.DIFFICULT else 1) + int(profile == "sceptical")
    for _ in range(count):
        await say(service, session, CLOSE)
    state = session.roleplay
    assert state.completion_reason == "success"
    assert state.dialogue.outcome == "boundary_held"
    assert state.dialogue.final_agreement is None
    assert state.dialogue.proposed_options == []
    assert state.dialogue.pressure_rounds == count
    assert state.decisions[-1].character_profile == profile
    if profile == "sceptical":
        assert "still wish" in session.turns[-1].content


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario,opening", [("boundary", REFUSAL), ("relationship", OPENING),
    ("workload", "I am overloaded with tasks. Could you help me prioritise?")])
async def test_same_opening_produces_profile_specific_objections(scenario, opening):
    objections = []
    for profile in PROFILES:
        service, session = await start(scenario, profile)
        await say(service, session, opening)
        objections.append(session.roleplay.dialogue.objection)
    assert len(set(objections)) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("level", list(Difficulty))
async def test_relationship_next_step(profile, level):
    service, session = await start("relationship", profile, level)
    await say(service, session, OPENING)
    assert session.roleplay.dialogue.stage == "perspective"
    await say(service, session, REQUEST)
    assert session.roleplay.dialogue.stage == "agree"
    await say(service, session, "Agreed.")
    assert session.roleplay.completion_reason == "success"
    assert session.roleplay.dialogue.outcome == "next_step"
    assert session.roleplay.dialogue.final_agreement == REQUEST


@pytest.mark.asyncio
async def test_relationship_disagreement_and_incompatible_request():
    service, session = await start("relationship", "rushed")
    await say(service, session, OPENING)
    await say(service, session, "I understand you are tired. Could we talk for 20 minutes tonight?")
    assert session.roleplay.dialogue.stage == "perspective"
    assert not session.roleplay.dialogue.proposed_options
    await say(service, session, "Let's agree to disagree and leave this unresolved.")
    assert session.roleplay.completion_reason == "unresolved"
    assert session.roleplay.dialogue.outcome == "unresolved"
    assert session.roleplay.dialogue.final_agreement is None
    assert "not a personal failure" in session.feedback.observed[-1]
    _, session = await service.rewind_roleplay(session.id, session.user_id)
    assert session.roleplay.dialogue.stage == "perspective"
    assert session.roleplay.dialogue.outcome is None


@pytest.mark.asyncio
async def test_difficulty_requires_additional_relationship_evidence():
    for level, stage in [(Difficulty.BEGINNER, "agree"), (Difficulty.DIFFICULT, "perspective")]:
        service, session = await start("relationship", "cooperative", level)
        await say(service, session, OPENING)
        await say(service, session, "I understand. Could we talk for 20 minutes on Saturday?")
        assert session.roleplay.dialogue.stage == stage


@pytest.mark.asyncio
async def test_workload_profiles_and_difficulty_change_requirements():
    for profile, level, expected in [("cooperative", Difficulty.BEGINNER, "agree"),
                                     ("sceptical", Difficulty.BEGINNER, "constraints"),
                                     ("cooperative", Difficulty.DIFFICULT, "constraints")]:
        service, session = await start("workload", profile, level)
        await say(service, session, "I am overloaded with tasks. Could you help me prioritise?")
        proposal = "I understand the report must be ready by Friday. Could we move the other tasks to Monday?"
        await say(service, session, proposal)
        assert session.roleplay.dialogue.stage == expected
        if expected == "constraints":
            await say(service, session, proposal + " We can check in on Thursday.")
        await say(service, session, "Agreed.")
        assert session.roleplay.dialogue.outcome == "agreement"


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", DEFINITIONS)
async def test_unrelated_messages_hit_cap_without_resolution(scenario):
    service, session = await start(scenario)
    for _ in range(8):
        await say(service, session, "The weather is pleasant.")
    assert session.roleplay.completion_reason == "maximum_turns"
    assert session.roleplay.dialogue.outcome is None


@pytest.mark.asyncio
async def test_profile_pressure_and_snapshots_survive_reload_and_rewind():
    service, session = await start("boundary", "sceptical", Difficulty.DIFFICULT)
    await say(service, session, REFUSAL)
    before = session.roleplay.model_copy(deep=True)
    await say(service, session, CLOSE)
    restored = Session.model_validate_json(session.model_dump_json())
    service.repository.sessions[session.id] = restored
    service = ConversationService(service.repository, generator=TemplateResponseGenerator())
    await service.set_roleplay_status(session.id, session.user_id, "pause")
    await service.set_roleplay_status(session.id, session.user_id, "resume")
    _, restored = await service.rewind_roleplay(session.id, session.user_id)
    assert restored.roleplay == before


@pytest.mark.parametrize("text", ["I cannot say no.", "I cannot take this on, but I'll do it.", "Maybe I cannot help.", "You should say no."])
def test_boundary_extraction_rejects_ambiguous_or_reversed_refusal(text):
    assert "refusal" not in features("boundary", text)


@pytest.mark.asyncio
async def test_relationship_negation_and_unrelated_confirmation():
    service, session = await start("relationship")
    await say(service, session, OPENING)
    await say(service, session, "I don't understand. I would not like us to talk on Saturday.")
    assert session.roleplay.dialogue.stage == "perspective"
    await say(service, session, REQUEST)
    for text in ["I will go shopping.", "I don't agree.", "Yes, if you change everything."]:
        await say(service, session, text)
        assert session.roleplay.dialogue.stage == "agree"
        assert session.roleplay.completion_reason is None


@pytest.mark.asyncio
async def test_profile_validation_and_unprofiled_compatibility():
    service, session = await start("boundary")
    for kwargs in [{"scenario_id": "deadline", "character_profile": "rushed"},
                   {"scenario_id": "boundary", "character_profile": "unknown"},
                   {"scenario_id": "boundary", "character_profile": "rushed", "attempt_purpose": "retry", "required_task_id": "boundary"}]:
        with pytest.raises(ValueError):
            await service.start_roleplay(session.id, session.user_id, level=Difficulty.INTERMEDIATE, pre_skipped=True, **kwargs)
    with pytest.raises(ValueError):
        StartRolePlayRequest(scenario_id="boundary", character_profile="unknown")
    legacy, _ = RolePlayService().start("boundary", Difficulty.BEGINNER)
    RolePlayService().plan_response(legacy, "I cannot do this.", EmotionState())
    assert legacy.completion_reason == "success"
    assert legacy.dialogue is None
    old = RolePlayState.model_validate({"scenario_id": "boundary"})
    assert old.character_profile is None and old.policy_version == "legacy-v1"


def test_profiled_difficulty_independent_of_affect_confidence():
    from app.services.scenario_dialogue import enable
    low, _ = RolePlayService().start("boundary", Difficulty.DIFFICULT)
    enable(low, "sceptical")
    high = low.model_copy(deep=True)
    a = RolePlayService().plan_response(low, REFUSAL, EmotionState(confidence=.01, arousal=1))
    b = RolePlayService().plan_response(high, REFUSAL, EmotionState(confidence=1, arousal=0))
    assert a == b
    assert low.difficulty == high.difficulty
    assert low.dialogue == high.dialogue
    assert low.policy_version == VERSION


@pytest.mark.asyncio
async def test_boundary_closure_cannot_concede_or_use_hostility():
    service, session = await start("boundary")
    await say(service, session, REFUSAL)
    await say(service, session, REFUSAL)
    assert session.roleplay.dialogue.stage == "close"
    for message in ["Thank you, I changed my mind and I will help.", "Thanks, you idiot."]:
        await say(service, session, message)
        assert session.roleplay.completion_reason is None
    await say(service, session, CLOSE)
    assert session.roleplay.dialogue.outcome == "boundary_held"


@pytest.mark.asyncio
async def test_rushed_relationship_does_not_accept_unrelated_weekend_mention():
    service, session = await start("relationship", "rushed")
    await say(service, session, OPENING)
    await say(service, session, "I understand. Could we talk tonight? The weekend is impossible.")
    assert session.roleplay.dialogue.stage == "perspective"
    await say(service, session, "We shouldn't stop here.")
    assert session.roleplay.completion_reason is None


@pytest.mark.asyncio
async def test_rushed_workload_asks_for_concise_priorities():
    service, session = await start("workload", "rushed")
    await say(service, session, "I am overloaded with tasks. Could you help me prioritise?")
    proposal = "I understand the report must be ready by Friday. Could we move the other tasks to Monday?"
    await say(service, session, proposal + " I have more details about this task." * 6)
    assert session.roleplay.decisions[-1].action == "ask_concise_priorities"
    await say(service, session, proposal)
    assert session.roleplay.dialogue.stage == "agree"


def test_workload_check_must_be_before_delivery():
    assert "check_in" not in features("workload", "We can check in on Saturday.")
    assert "check_in" not in features("workload", "We can check in on Saturday. Thursday is busy.")
    assert "check_in" in features("workload", "We can review progress on Thursday.")
