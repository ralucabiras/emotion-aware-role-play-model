from datetime import timedelta
from uuid import uuid4

import pytest

from app.api.routes import participant_study_progress, pilot_dataset
from app.core.config import settings
from app.models.domain import (
    Difficulty,
    StudyConsentRecord,
    StudyEligibilityRecord,
    StudyQuestionnaire,
    StudyRecord,
    User,
    utcnow,
)
from app.repositories.memory import MemoryRepository
from app.services.eligibility import eligibility_version


async def enrolled_cohort():
    repository = MemoryRepository()
    user = User(
        email="completion@example.com", password_hash="unused", consented_at=utcnow(),
        pilot_enrolled_at=utcnow(),
        study_consent=StudyConsentRecord(version=settings.study_consent_version, protocol_version=settings.study_protocol_version),
        study_eligibility=StudyEligibilityRecord(version=eligibility_version(), protocol_version=settings.study_protocol_version),
    )
    await repository.create_user(user)
    return repository, user


async def add_task(repository, user, scenario, reason="success", post=True, **overrides):
    record = StudyRecord(
        user_id=user.id, participant_id=user.participant_id, session_id=uuid4(),
        consent_version=user.study_consent.version, protocol_version=settings.study_protocol_version,
        enrolled_at=user.pilot_enrolled_at, session_created_at=utcnow(), last_activity_at=utcnow(),
        retention_expires_at=utcnow()+timedelta(days=1),
        scenario_id=scenario, attempt_purpose="required", required_task_id=scenario, difficulty=Difficulty.INTERMEDIATE, completion_reason=reason,
        questionnaires={"post": StudyQuestionnaire(phase="post", confidence=1, realism=4, usefulness=7)} if post else {},
    ).model_copy(update=overrides)
    await repository.save_study_record(record)
    return record


@pytest.mark.asyncio
@pytest.mark.parametrize("reason,expected", [
    ("success", 3), ("maximum_turns", 3), ("user_finished", 3),
    ("safety_interruption", 0), ("technical_failure", 0), ("unknown", 0), (None, 0),
])
async def test_completion_counts_require_an_explicit_qualifying_reason(reason, expected):
    repository, user = await enrolled_cohort()
    for scenario in ("workload", "boundary", "relationship"):
        # Interrupted legacy records can contain post-ratings; they must still fail.
        await add_task(repository, user, scenario, reason=reason)
    _, rows, dashboard = await pilot_dataset(repository)
    assert dashboard["sessions"] == 3
    assert dashboard["completed_rehearsals"] == rows[0]["completed_rehearsals"] == expected
    assert dashboard["completion_rate"] == expected / 3
    assert dashboard["protocol_completers"] == int(expected == 3)
    assert dashboard["protocol_completion_rate"] == int(expected == 3)
    assert rows[0]["protocol_complete"] is (expected == 3)
    assert rows[0]["completion_status"] == ("complete" if expected else "in_progress")
    assert dashboard["scenario_completions"] == ({"workload": 1, "boundary": 1, "relationship": 1} if expected else {})
    assert dashboard["difficulty_completions"] == ({"intermediate": 3} if expected else {})


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["all", "confidence", "realism", "usefulness", "wrong_phase"])
async def test_partial_or_missing_post_ratings_do_not_complete_protocol(missing):
    repository, user = await enrolled_cohort()
    await add_task(repository, user, "workload")
    await add_task(repository, user, "boundary")
    values = {"phase": "post", "confidence": 4, "realism": 4, "usefulness": 4}
    if missing == "wrong_phase":
        values["phase"] = "pre"
    elif missing != "all":
        values[missing] = None
    questionnaires = {} if missing == "all" else {"post": StudyQuestionnaire(**values)}
    await add_task(repository, user, "relationship", questionnaires=questionnaires)
    _, rows, dashboard = await pilot_dataset(repository)
    # Rehearsal completion and full protocol completion are separate measures.
    assert dashboard["completed_rehearsals"] == 3
    assert dashboard["protocol_completers"] == 0
    assert rows[0]["protocol_complete"] is False


@pytest.mark.asyncio
async def test_protocol_completion_requires_current_protocol_all_scenarios_and_intermediate():
    repository, user = await enrolled_cohort()
    await add_task(repository, user, "workload")
    await add_task(repository, user, "workload")  # A duplicate is not another required task.
    await add_task(repository, user, "boundary")
    await add_task(repository, user, "relationship", difficulty=Difficulty.BEGINNER)
    await add_task(repository, user, "relationship", protocol_version="another-protocol")
    await add_task(repository, user, "custom_example")
    _, rows, dashboard = await pilot_dataset(repository)
    assert dashboard["sessions"] == dashboard["completed_rehearsals"] == 5
    assert dashboard["protocol_completers"] == 0
    assert rows[0]["protocol_complete"] is False
    await add_task(repository, user, "relationship", reason="user_finished")
    _, rows, dashboard = await pilot_dataset(repository)
    assert dashboard["protocol_completers"] == 1
    assert rows[0]["protocol_complete"] is True


@pytest.mark.asyncio
async def test_participant_checklist_uses_durable_records_and_protocol_order():
    repository, user = await enrolled_cohort()
    progress = await participant_study_progress(user, repository)
    assert [task["scenario_id"] for task in progress["tasks"]] == ["workload", "boundary", "relationship"]
    assert all(task["difficulty"] == "intermediate" for task in progress["tasks"])
    assert progress["completed_tasks"] == 0 and progress["next_task_id"] == "workload"
    await add_task(repository, user, "workload", difficulty=Difficulty.BEGINNER)
    assert (await participant_study_progress(user, repository))["next_task_id"] == "workload"
    # A completed durable record counts even after the conversation has expired.
    await add_task(repository, user, "workload")
    progress = await participant_study_progress(user, repository)
    assert progress["tasks"][0]["status"] == "complete"
    assert progress["completed_tasks"] == 1 and progress["next_task_id"] == "boundary"
    await add_task(repository, user, "boundary", post=False)
    progress = await participant_study_progress(user, repository)
    assert progress["tasks"][1]["status"] == "incomplete"
    assert progress["next_task_id"] == "relationship"
    await add_task(repository, user, "relationship", reason="safety_interruption")
    progress = await participant_study_progress(user, repository)
    assert progress["completed_tasks"] == 1 and progress["next_task_id"] is None


@pytest.mark.asyncio
async def test_checklist_resumes_active_attempt_and_waits_for_post_decision():
    from app.models.domain import StudyLifecycle
    from app.services.conversation_service import ConversationService
    from app.services.llm_service import TemplateResponseGenerator

    repository, user = await enrolled_cohort()
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    workspace = await service.create_session(user.id)
    session, _, _ = await service.start_roleplay(workspace.id, user.id, "workload", Difficulty.INTERMEDIATE, pre_skipped=True, attempt_purpose="required", required_task_id="workload")
    progress = await participant_study_progress(user, repository)
    assert progress["tasks"][0]["status"] == "in_progress"
    assert progress["tasks"][0]["session_id"] == str(session.id)
    await service.set_roleplay_status(session.id, user.id, "finish")
    assert (await participant_study_progress(user, repository))["tasks"][0]["status"] == "awaiting_ratings"
    await service.submit_questionnaire(session.id, user.id, "post", {}, skipped=True, post_token=session.post_questionnaire_token)
    progress = await participant_study_progress(user, repository)
    assert progress["next_task_id"] == "boundary" and progress["completed_tasks"] == 0
    await repository.save_study_lifecycle(StudyLifecycle(protocol_version=settings.study_protocol_version, end_date=utcnow().date()-timedelta(days=1)))
    progress = await participant_study_progress(user, repository)
    assert progress["available"] is False and progress["next_task_id"] is None


@pytest.mark.asyncio
async def test_participant_progress_does_not_include_another_participant():
    from fastapi import HTTPException

    repository, user = await enrolled_cohort()
    other = user.model_copy(update={"id": uuid4(), "participant_id": uuid4(), "email": "other@example.com"})
    await repository.create_user(other)
    await add_task(repository, other, "workload")
    assert (await participant_study_progress(user, repository))["completed_tasks"] == 0
    user.study_eligibility = None
    with pytest.raises(HTTPException) as error:
        await participant_study_progress(user, repository)
    assert error.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", ["additional", "retry", "legacy_unknown", "required"])
async def test_later_success_never_replaces_first_incomplete_required_attempt(purpose):
    import csv
    import io

    from app.api.routes import build_research_csv, research_export

    repository, user = await enrolled_cohort()
    first = await add_task(repository, user, "workload", post=False)
    later = await add_task(repository, user, "workload", attempt_purpose=purpose)
    await add_task(repository, user, "boundary")
    await add_task(repository, user, "relationship")
    progress = await participant_study_progress(user, repository)
    assert progress["tasks"][0]["status"] == "incomplete"
    assert progress["completed_tasks"] == 2
    assert (await pilot_dataset(repository))[2]["protocol_completers"] == 0
    for frozen in [False, True]:
        content, _, _ = await build_research_csv(repository, frozen)
        rows = list(csv.DictReader(io.StringIO(content)))
        workload = [row for row in rows if row["scenario_id"] == "workload"]
        assert [row["primary_attempt"] for row in workload] == ["True", "False"]
        assert [row["primary_task_complete"] for row in workload] == ["False", "False"]
        assert workload[1]["attempt_purpose"] == purpose
    personal = await research_export(user, repository)
    flags = {row["session_id"]: row["primary_attempt"] for row in personal["records"]}
    assert flags[str(first.session_id)] is True and flags[str(later.session_id)] is False
    # Selection is by start/creation time, never last activity or repository order.
    first.last_activity_at = later.last_activity_at + timedelta(days=1)
    await repository.save_study_record(first)
    assert (await participant_study_progress(user, repository))["completed_tasks"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", ["additional", "retry", "legacy_unknown"])
async def test_practice_and_legacy_records_do_not_start_required_checklist(purpose):
    repository, user = await enrolled_cohort()
    for scenario in ("workload", "boundary", "relationship"):
        await add_task(repository, user, scenario, attempt_purpose=purpose)
    progress = await participant_study_progress(user, repository)
    assert all(task["status"] == "not_started" for task in progress["tasks"])
    assert progress["next_task_id"] == "workload"
    assert (await pilot_dataset(repository))[2]["protocol_completers"] == 0


@pytest.mark.asyncio
async def test_required_start_validates_purpose_and_preserves_first_attempt_after_deletion():
    from app.services.conversation_service import ConversationService
    from app.services.llm_service import TemplateResponseGenerator

    repository, user = await enrolled_cohort()
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    workspace = await service.create_session(user.id)
    for scenario, level, association in [("workload", Difficulty.BEGINNER, "workload"),
                                         ("workload", Difficulty.INTERMEDIATE, "boundary"),
                                         ("workload", Difficulty.INTERMEDIATE, None)]:
        with pytest.raises(ValueError):
            await service.start_roleplay(workspace.id, user.id, scenario, level, pre_skipped=True,
                                         attempt_purpose="required", required_task_id=association)
    session, _, _ = await service.start_roleplay(workspace.id, user.id, "workload", Difficulty.INTERMEDIATE,
                                               pre_skipped=True, attempt_purpose="required", required_task_id="workload")
    assert session.roleplay.attempt_purpose == "required"
    record = next(record for record in await repository.list_study_records(user.id) if record.session_id == session.id)
    assert record.required_task_id == "workload" and record.attempt_purpose == "required"
    await repository.delete_session(session.id, user.id)
    workspace = await service.create_session(user.id)
    with pytest.raises(ValueError, match="already has an attempt"):
        await service.start_roleplay(workspace.id, user.id, "workload", Difficulty.INTERMEDIATE,
                                     pre_skipped=True, attempt_purpose="required", required_task_id="workload")
    retry, _, _ = await service.start_roleplay(workspace.id, user.id, "workload", Difficulty.INTERMEDIATE,
                                             pre_skipped=True, attempt_purpose="retry", required_task_id="workload")
    assert retry.roleplay.attempt_purpose == "retry"
    assert (await participant_study_progress(user, repository))["tasks"][0]["status"] == "incomplete"
