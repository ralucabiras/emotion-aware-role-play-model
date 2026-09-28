"""Synthetic preparation and action-card cases; no participant data."""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.domain import Difficulty
from app.repositories.memory import MemoryRepository
from app.schemas.chat import ActionCardRequest, CustomScenarioRequest, PreparationRequest
from app.services.conversation_service import ConversationService, SessionNotFoundError
from app.services.llm_service import TemplateResponseGenerator
from app.services.preparation import action_card_draft, custom_scenario, prepare_brief, save_action_card

INPUT = dict(who="my housemate", happened="I have been doing the dishes every evening this week.",
             desired_outcome="I would like us to share the dishes on weekdays.", difficult_part="I worry they will feel blamed.")


async def practice(repository=None):
    service = ConversationService(repository or MemoryRepository(), generator=TemplateResponseGenerator())
    session = await service.create_session(uuid4())
    brief = prepare_brief(PreparationRequest(**INPUT))
    scenario = custom_scenario(brief, f"custom_{uuid4().hex}")
    session, _, _ = await service.start_roleplay(session.id, session.user_id, scenario.id, Difficulty.INTERMEDIATE,
                                               custom=scenario, pre_skipped=True)
    return service, session, scenario


@pytest.mark.asyncio
async def test_prepared_generic_rehearsal_objection_and_edit_isolation():
    service, session, scenario = await practice()
    scenario.preparation.likely_objection = "An edit made after starting"
    assert session.roleplay.scenario.preparation.likely_objection != scenario.preparation.likely_objection
    reply, _, session = await service.chat(session.id, session.user_id, "I need help with the dishes this week.")
    assert reply.content == session.roleplay.scenario.preparation.likely_objection
    assert session.roleplay.status == "active" and session.feedback is None
    assert session.roleplay.success_progress <= .5
    await service.chat(session.id, session.user_id, "Clouds are lovely.")
    assert session.roleplay.status == "active"
    _, _, session = await service.chat(session.id, session.user_id, "Could you do the dishes on Monday?")
    assert session.roleplay.status == "completed"
    assert session.roleplay.policy_version == "prepared-generic-v1"
    assert session.roleplay.dialogue is None
    assert session.feedback.generation_source != "openai"


@pytest.mark.asyncio
async def test_card_is_separate_and_draft_excludes_later_reflection():
    service, session, _ = await practice()
    await service.chat(session.id, session.user_id, "I need help with the dishes this week.")
    await service.chat(session.id, session.user_id, "I cannot do every evening. Could you do Monday?")
    await service.chat(session.id, session.user_id, "Later reflection that must not be suggested.")
    draft = action_card_draft(session)
    assert "Later reflection" not in draft.model_dump_json()
    assert draft.main_request == INPUT["desired_outcome"]
    assert draft.source == "template-v1" and session.action_card is None
    before = (session.feedback.model_dump_json(), session.roleplay.model_dump_json(), session.questionnaires.copy(), list(session.research_events))
    request = ActionCardRequest(expected_version=session.version, opening_sentence="Can we talk tonight?",
        main_request="Could we share weekday dishes?", boundary_or_fallback="I can do Mondays, but not every night.", reminder="Pause and listen.")
    saved = await save_action_card(service, session.id, session.user_id, request)
    assert saved.action_card.source == "user-edited" and saved.action_card.reminder == "Pause and listen."
    assert (saved.feedback.model_dump_json(), saved.roleplay.model_dump_json(), saved.questionnaires, saved.research_events) == before
    assert action_card_draft(saved) == saved.action_card
    with pytest.raises(ValueError, match="session changed"):
        await save_action_card(service, session.id, session.user_id, request)
    with pytest.raises(SessionNotFoundError):
        await save_action_card(service, session.id, uuid4(), request)


@pytest.mark.asyncio
async def test_card_rewind_and_branch_do_not_reuse_old_plan():
    from test_branching import completed, fork

    service, parent = await completed()
    parent = await save_action_card(service, parent.id, parent.user_id, ActionCardRequest(expected_version=parent.version,
        opening_sentence="Original plan", main_request="Original request", boundary_or_fallback="Original fallback", reminder="Original reminder"))
    child = await fork(service, parent)
    assert child.action_card is None
    _, parent = await service.rewind_roleplay(parent.id, parent.user_id)
    assert parent.action_card is None
    with pytest.raises(ValueError, match="Finish the rehearsal"):
        action_card_draft(parent)


@pytest.mark.asyncio
async def test_interruption_does_not_suggest_crisis_words():
    service, session, _ = await practice()
    await service.chat(session.id, session.user_id, "I want to kill myself")
    draft = action_card_draft(session)
    assert not draft.source_turn_ids
    assert "kill myself" not in draft.model_dump_json()


@pytest.mark.asyncio
async def test_unknown_legacy_boundary_does_not_suggest_reflection():
    service, session, _ = await practice()
    await service.chat(session.id, session.user_id, "I need help with dishes this week.")
    await service.set_roleplay_status(session.id, session.user_id, "finish")
    await service.chat(session.id, session.user_id, "Later private reflection")
    session.roleplay.completed_at = session.roleplay.measurement_ended_at = None
    assert action_card_draft(session).source_turn_ids == []


def test_preparation_validation_and_old_custom_compatibility():
    brief = prepare_brief(PreparationRequest(**INPUT))
    assert brief.character == INPUT["who"] and brief.situation == INPUT["happened"]
    assert brief.preparation.source == "template-v1"
    legacy = CustomScenarioRequest(title="Old scenario", character="manager", situation="An old workload situation",
        user_objective="Ask for help with tasks", opening_line="What is happening?", skills=["clear request"])
    assert custom_scenario(legacy, "custom_old").preparation is None
    with pytest.raises(ValidationError):
        PreparationRequest(**{**INPUT, "who": " "})
    with pytest.raises(ValidationError):
        ActionCardRequest(expected_version=1, opening_sentence=" ", main_request="request", boundary_or_fallback="fallback", reminder="reminder")
