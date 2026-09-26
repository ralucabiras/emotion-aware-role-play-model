"""Synthetic engineering fixtures, not participant evidence."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.domain import Difficulty, RolePlayStatus, Session
from app.repositories.memory import MemoryRepository
from app.services.conversation_service import ConversationService
from app.services.llm_service import OpenAIResponseGenerator, RolePlayWording, TemplateResponseGenerator
from app.services.workload_dialogue import features

OPENING = "I have too many tasks and 12 hours of work. Could you help me prioritise?"
PROPOSAL = "I understand the report must be ready by Friday. Could we move the other tasks to Monday?"
CONFIRM = "Agreed, I will carry out that plan."

async def start():
    service = ConversationService(MemoryRepository(), generator=TemplateResponseGenerator())
    session = await service.create_session(uuid4())
    session, _, _ = await service.start_roleplay(session.id, session.user_id, "workload", Difficulty.INTERMEDIATE, pre_skipped=True)
    return service, session

async def say(service, session, message):
    return (await service.chat(session.id, session.user_id, message))[2]

@pytest.mark.asyncio
async def test_complete_reload_rewind_and_measurement_boundary():
    service, session = await start()
    initial_emotion = session.emotion_state.model_copy(deep=True)
    await say(service, session, OPENING)
    assert session.roleplay.dialogue.stage == "constraints"
    assert session.feedback is None
    await service.set_roleplay_status(session.id, session.user_id, "pause")
    await service.set_roleplay_status(session.id, session.user_id, "resume")
    # Round-trip persisted representation with a fresh service instance.
    restored = Session.model_validate_json(session.model_dump_json())
    service.repository.sessions[session.id] = restored
    service = ConversationService(service.repository, generator=TemplateResponseGenerator())
    session = await say(service, restored, PROPOSAL)
    assert session.roleplay.dialogue.stage == "agree"
    session = await say(service, session, CONFIRM)
    assert session.roleplay.completion_reason == "success"
    assert session.roleplay.dialogue.final_agreement == PROPOSAL
    for decision in session.roleplay.decisions:
        assert decision.user_turn_id in [t.id for t in session.turns]
        assert decision.assistant_turn_id in [t.id for t in session.turns]
        assert decision.generation.source == "deterministic_roleplay"
    assert session.roleplay.decisions[0].before.emotion_state == initial_emotion
    _, session = await service.rewind_roleplay(session.id, session.user_id)
    assert session.roleplay.dialogue.stage == "agree"
    assert session.roleplay.dialogue.final_agreement is None
    assert len(session.roleplay.decisions) == 2
    assert session.feedback is None
    await say(service, session, CONFIRM)
    frozen = session.roleplay.model_dump_json()
    feedback = session.feedback.model_dump_json()
    await say(service, session, "What should I reflect on?")
    assert session.roleplay.model_dump_json() == frozen
    assert session.feedback.model_dump_json() == feedback

@pytest.mark.asyncio
@pytest.mark.parametrize("reply", ["I don't agree", "Yes, but I cannot do that", "Maybe I will", "Yes if I get help", "I agree?", "The weather is pleasant", "I can play piano", "I will go shopping", "I agree to nothing"])
async def test_invalid_confirmation_never_succeeds(reply):
    service, session = await start()
    for text in [OPENING, PROPOSAL, reply]:
        await say(service, session, text)
    assert session.roleplay.dialogue.stage == "agree"
    assert session.roleplay.status == RolePlayStatus.ACTIVE

@pytest.mark.asyncio
async def test_unrelated_limit_and_early_finish():
    service, session = await start()
    for _ in range(8):
        await say(service, session, "The weather is pleasant")
    assert session.roleplay.completion_reason == "maximum_turns"
    assert session.roleplay.dialogue.final_agreement is None
    assert "without a confirmed agreement" in session.turns[-1].content
    service, session = await start()
    await say(service, session, OPENING)
    await service.set_roleplay_status(session.id, session.user_id, "finish")
    assert session.roleplay.completion_reason == "user_finished"

@pytest.mark.asyncio
async def test_safety_interrupts_without_inventing_evidence():
    service, session = await start()
    await say(service, session, OPENING)
    await say(service, session, "I want to kill myself")
    assert session.roleplay.status == RolePlayStatus.INTERRUPTED
    assert session.roleplay.turn == 1
    assert session.roleplay.decisions[-1].after.status == RolePlayStatus.INTERRUPTED
    with pytest.raises(ValueError):
        await service.rewind_roleplay(session.id, session.user_id)

@pytest.mark.parametrize("text", ["I do not agree", "I cannot move the other tasks to Monday", "I won't finish the report by Friday"])
def test_negated_features(text):
    assert not features(text)

@pytest.mark.asyncio
async def test_online_wording_cannot_override_controller(monkeypatch):
    from app.core.config import settings
    service, session = await start()
    generator = OpenAIResponseGenerator()
    generator.client = SimpleNamespace(responses=SimpleNamespace(parse=AsyncMock(return_value=SimpleNamespace(
        output_parsed=RolePlayWording(character_action="raise_delivery_constraint", dialogue="Agreed, everything is complete.")))))
    monkeypatch.setattr(settings, "openai_roleplay_enabled", True)
    text, metadata = await generator.generate_roleplay(session, session.roleplay.scenario, "raise_delivery_constraint", "The report is due Friday.")
    assert text == "The report is due Friday."
    assert metadata.fallback_reason == "unverified_policy_wording"

@pytest.mark.asyncio
async def test_legacy_session_keeps_original_completion():
    service, session = await start()
    session.roleplay.dialogue = None
    session.roleplay.policy_version = "legacy-v1"
    await say(service, session, "I need the deadline moved to Friday because of the workload.")
    assert session.roleplay.completion_reason == "success"
    assert not session.roleplay.decisions


@pytest.mark.parametrize("opening,proposal,confirmation", [
    ("My workload has too many tasks. Please help me prioritise.", "I recognise the client needs the report by Friday. We can postpone the internal tasks to next week.", "Yes."),
    ("I am overloaded with project tasks. Can we prioritise?", "I understand the report must be done for Friday. Could we delegate the admin tasks to a colleague?", "That works."),
])
@pytest.mark.asyncio
async def test_supported_paraphrases(opening, proposal, confirmation):
    service, session = await start()
    for message in [opening, proposal, confirmation]:
        await say(service, session, message)
    assert session.roleplay.completion_reason == "success"
