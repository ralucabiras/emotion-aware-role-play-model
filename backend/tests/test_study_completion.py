from datetime import timedelta
from uuid import uuid4

import pytest

from app.api.routes import pilot_dataset
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
        scenario_id=scenario, difficulty=Difficulty.INTERMEDIATE, completion_reason=reason,
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
