"""Synthetic branch fixtures, not evidence of participant outcomes."""
import asyncio
import csv
import io
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.config import settings
from app.models.domain import Difficulty, Session, StudyConsentRecord, StudyEligibilityRecord, User, utcnow
from app.repositories.memory import MemoryRepository
from app.services.branching import compare_branch, create_branch
from app.services.conversation_service import ConversationService, SessionNotFoundError, dialogue_snapshot
from app.services.eligibility import eligibility_version
from app.services.llm_service import OpenAIResponseGenerator, TemplateResponseGenerator
from app.services.research_export import export_research_rows

OPENING = "I have too many tasks and 12 hours of work. Could you help me prioritise?"
PROPOSAL = "I understand the report must be ready by Friday. Could we move the other tasks to Monday?"
CONFIRM = "Agreed, I will carry out that plan."


async def completed(repository=None, profile=None):
    repository = repository or MemoryRepository()
    user = User(email=f"branch-{uuid4()}@example.com", password_hash="unused", consented_at=utcnow())
    user.pilot_enrolled_at = utcnow()
    user.study_consent = StudyConsentRecord(version=settings.study_consent_version,
        protocol_version=settings.study_protocol_version, accepted_at=user.pilot_enrolled_at)
    user.study_eligibility = StudyEligibilityRecord(version=eligibility_version(), protocol_version=settings.study_protocol_version)
    await repository.create_user(user)
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    session = await service.create_session(user.id)
    session, _, _ = await service.start_roleplay(session.id, user.id, "workload", Difficulty.INTERMEDIATE,
        character_profile=profile, pre_skipped=True)
    for message in [OPENING, PROPOSAL, CONFIRM]:
        _, _, session = await service.chat(session.id, user.id, message)
    assert session.roleplay.status == "completed"
    return service, session


async def fork(service, parent, index=1, request_id=None):
    return await create_branch(service, parent.id, parent.user_id, parent.roleplay.decisions[index].user_turn_id,
                               parent.version, request_id or uuid4())


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", [None, "cooperative"])
async def test_exact_snapshot_parent_immutability_and_continuation_feedback(profile):
    service, parent = await completed(profile=profile)
    await service.submit_questionnaire(parent.id, parent.user_id, "post", {"confidence": 4, "realism": 5, "usefulness": 6}, post_token=parent.post_questionnaire_token)
    await service.save_takeaway(parent.id, parent.user_id, "Private original takeaway")
    parent = await service.get_session(parent.id, parent.user_id)
    original = parent.model_dump_json()
    before = parent.roleplay.decisions[1].before
    child = await fork(service, parent)
    assert dialogue_snapshot(child) == before
    assert child.branch.before == before
    assert child.roleplay.scenario == parent.roleplay.scenario
    assert child.roleplay.character_profile == profile
    assert child.turns == parent.turns[:3]
    assert not child.feedback and not child.takeaway and not child.questionnaires and not child.questionnaire_skips
    assert not child.post_questionnaire_token and not child.roleplay.completed_at and not child.roleplay.measurement_ended_at
    assert child.roleplay.attempt_purpose == "retry" and child.roleplay.required_task_id is None
    assert parent.model_dump_json() == original
    for message in [PROPOSAL, CONFIRM]:
        _, _, child = await service.chat(child.id, child.user_id, message)
    assert child.feedback.session_id == child.id
    assert child.feedback.evidence_scope == "continuation"
    assert all(1 not in metric.evidence_turns for metric in child.feedback.metrics)
    assert child.feedback.comparisons == []
    assert parent.model_dump_json() == original
    comparison = await compare_branch(service, child.id, child.user_id)
    assert len(comparison["shared_context"]) == 3
    assert len(comparison["original"]["turns"]) == len(comparison["alternative"]["turns"]) == 4
    assert all(item.turn != 1 for item in comparison["alternative"]["evidence"])


@pytest.mark.asyncio
async def test_copied_activity_is_not_recounted_in_records_or_csv():
    service, parent = await completed()
    child = await fork(service, parent)
    records = await service.repository.list_study_records(child.user_id)
    record = next(item for item in records if item.session_id == child.id)
    assert record.turn_count == 0 and record.generation_source_counts == {}
    assert record.copied_context_turn_count == 3 and record.is_branch
    assert record.feedback_evidence_scope == "continuation"
    _, _, child = await service.chat(child.id, child.user_id, PROPOSAL)
    csv_text, _, _ = await export_research_rows(service.repository, [await service.repository.get_user(child.user_id)])
    row = next(row for row in csv.DictReader(io.StringIO(csv_text)) if row["session_id"] == str(child.id))
    assert row["turn_count"] == "2" and row["copied_context_turn_count"] == "3"
    assert row["is_branch"] == "True" and row["primary_attempt"] == "False"
    assert row["feedback_evidence_scope"] == "continuation"
    assert OPENING not in csv_text and PROPOSAL not in csv_text


@pytest.mark.asyncio
async def test_reload_deletion_and_rewind_preserve_child_context():
    service, parent = await completed()
    child = await fork(service, parent)
    with pytest.raises(ValueError, match="Shared context"):
        await service.rewind_roleplay(child.id, child.user_id)
    service.repository.sessions[child.id] = Session.model_validate_json(child.model_dump_json())
    await service.delete_session(parent.id, parent.user_id)
    comparison = await compare_branch(service, child.id, child.user_id)
    assert comparison["original"] is None and "deleted or expired" in comparison["unavailable_reason"]
    _, _, child = await service.chat(child.id, child.user_id, PROPOSAL)
    _, child = await service.rewind_roleplay(child.id, child.user_id)
    assert dialogue_snapshot(child) == child.branch.before
    assert [turn.id for turn in child.turns] == child.branch.copied_turn_ids
    await service.repository.delete_user(child.user_id)
    assert await service.repository.get_session(child.id, child.user_id) is None


@pytest.mark.asyncio
async def test_idempotency_stale_versions_and_ownership():
    service, parent = await completed()
    request_id = uuid4()
    children = await asyncio.gather(*(fork(service, parent, request_id=request_id) for _ in range(2)))
    assert children[0].id == children[1].id
    assert len(await service.list_sessions(parent.user_id)) == 2
    with pytest.raises(ValueError, match="request was already used"):
        await fork(service, parent, index=0, request_id=request_id)
    with pytest.raises(ValueError, match="original changed"):
        await create_branch(service, parent.id, parent.user_id, parent.roleplay.decisions[0].user_turn_id, parent.version-1, uuid4())
    with pytest.raises(SessionNotFoundError):
        await create_branch(service, parent.id, uuid4(), parent.roleplay.decisions[0].user_turn_id, parent.version, uuid4())
    with pytest.raises(SessionNotFoundError):
        await compare_branch(service, children[0].id, uuid4())


@pytest.mark.asyncio
async def test_nested_branches_freeze_context_and_use_deterministic_wording():
    service, parent = await completed()
    child = await fork(service, parent)
    generator = OpenAIResponseGenerator()
    generator.moderate = AsyncMock(return_value=False)
    generator.generate_roleplay = AsyncMock(side_effect=AssertionError("Branch must use deterministic wording"))
    service.generator = generator
    for text in [PROPOSAL, CONFIRM]:
        turn, _, child = await service.chat(child.id, child.user_id, text)
        assert turn.generation.source == "deterministic_roleplay"
    generator.generate_roleplay.assert_not_called()
    with pytest.raises(ValueError, match="Shared context"):
        await fork(service, child, index=0)
    grandchild = await fork(service, child, index=2)
    assert grandchild.branch.branch_group_id == parent.id
    assert grandchild.branch.parent_session_id == child.id
    assert dialogue_snapshot(grandchild) == child.roleplay.decisions[2].before
    grandchild.roleplay.policy_version = "unsupported-future"
    with pytest.raises(ValueError, match="saved policy is unavailable"):
        await service.chat(grandchild.id, grandchild.user_id, CONFIRM)


@pytest.mark.asyncio
async def test_boundary_demonstration_apology_and_clear_refusal():
    from test_scenario_dialogue import CLOSE, REFUSAL, say, start

    service, parent = await start("boundary", "sceptical")
    parent = await say(service, parent, "Sorry, sorry, maybe I could help.")
    await service.set_roleplay_status(parent.id, parent.user_id, "finish")
    frozen = parent.model_dump_json()
    child = await fork(service, parent, index=0)
    assert child.roleplay.dialogue.stage == "refuse"
    for text in [REFUSAL, CLOSE, CLOSE]:
        child = await say(service, child, text)
    result = await compare_branch(service, child.id, child.user_id)
    assert result["original"]["evidence"][0].excessive_apology
    assert result["alternative"]["evidence"][0].maintained_boundary
    assert result["original"]["outcome"] is None
    assert result["alternative"]["outcome"] == "boundary_held"
    assert result["alternative"]["agreement"] is None
    assert parent.model_dump_json() == frozen


@pytest.mark.asyncio
async def test_relationship_branch_can_have_a_different_recorded_outcome():
    from test_scenario_dialogue import OPENING as RELATIONSHIP_OPENING
    from test_scenario_dialogue import REQUEST, say, start

    service, parent = await start("relationship", "rushed")
    for text in [RELATIONSHIP_OPENING, REQUEST, "Agreed."]:
        parent = await say(service, parent, text)
    child = await fork(service, parent, index=1)
    child = await say(service, child, "Let's agree to disagree and leave this unresolved.")
    result = await compare_branch(service, child.id, child.user_id)
    assert result["original"]["outcome"] == "next_step"
    assert result["alternative"]["outcome"] == "unresolved"
    assert child.roleplay.character_profile == "rushed"


@pytest.mark.asyncio
async def test_changed_source_is_not_silently_compared_and_reflection_is_excluded():
    service, parent = await completed()
    child = await fork(service, parent)
    await service.chat(parent.id, parent.user_id, "Later reflection")
    comparison = await compare_branch(service, child.id, child.user_id)
    assert comparison["original"] and all(turn.content != "Later reflection" for turn in comparison["original"]["turns"])
    parent.roleplay.decisions.pop()
    comparison = await compare_branch(service, child.id, child.user_id)
    assert comparison["original"] is None and "changed" in comparison["unavailable_reason"]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["legacy", "required", "missing", "unknown_version", "paused_snapshot"])
async def test_unsupported_points_are_rejected(change):
    service, parent = await completed()
    point = parent.roleplay.decisions[1].user_turn_id
    if change == "legacy": parent.roleplay.dialogue = None
    if change == "required": parent.roleplay.attempt_purpose = "required"
    if change == "missing": parent.roleplay.decisions = []
    if change == "unknown_version": parent.roleplay.scoring_version = "future-version"
    if change == "paused_snapshot": parent.roleplay.decisions[1].before.status = "paused"
    with pytest.raises(ValueError, match="fresh attempt"):
        await create_branch(service, parent.id, parent.user_id, point, parent.version, uuid4())
    assert len(await service.list_sessions(parent.user_id)) == 1
