import csv
import io
import json
from datetime import timedelta
from uuid import uuid4

import pytest

from app.api.routes import build_research_csv
from app.core.config import settings
from app.models.domain import (
    ConversationTurn,
    Difficulty,
    FeedbackMetric,
    GenerationMetadata,
    ResearchEvent,
    Role,
    Session,
    StudyConsentRecord,
    StudyEligibilityRecord,
    StudyRecord,
    User,
    utcnow,
)
from app.repositories.memory import MemoryRepository
from app.services.conversation_service import ConversationService
from app.services.eligibility import eligibility_version
from app.services.llm_service import TemplateResponseGenerator
from app.services.research_export import CSV_FIELDS, CSV_SCHEMA_VERSION


def participant(email):
    return User(
        email=email, first_name="PRIVATE_NAME", password_hash="PRIVATE_HASH", consented_at=utcnow(),
        pilot_enrolled_at=utcnow(),
        study_consent=StudyConsentRecord(version=settings.study_consent_version, protocol_version=settings.study_protocol_version),
        study_eligibility=StudyEligibilityRecord(version=eligibility_version(), protocol_version=settings.study_protocol_version),
    )


@pytest.mark.asyncio
async def test_export_contains_scores_sources_and_zero_session_participants():
    repository = MemoryRepository()
    active, idle, excluded = [participant(f"{name}@example.com") for name in ("active", "idle", "excluded")]
    excluded.study_excluded_at = utcnow()
    for user in (active, idle, excluded):
        await repository.create_user(user)
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    workspace = await service.create_session(active.id)
    session, _, _ = await service.start_roleplay(workspace.id, active.id, "workload", Difficulty.INTERMEDIATE, pre_ratings={"confidence": 2, "anxiety": 6})
    await service.chat(session.id, active.id, "I need you to move the report deadline to Friday because I have 12 hours of work this week.")
    await service.submit_questionnaire(session.id, active.id, "post", {"confidence": 5, "realism": 6, "usefulness": 7}, post_token=session.post_questionnaire_token)
    session.takeaway = "PRIVATE_TAKEAWAY"
    session.research_events.append(ResearchEvent(name="custom_event", properties={"note": "PRIVATE_EVENT_TEXT"}))
    await service.save(session)

    live, count, participants = await build_research_csv(repository)
    rows = list(csv.DictReader(io.StringIO(live)))
    assert count == len(rows) == 2
    assert participants == 2
    attempt, idle_row = rows
    assert attempt["row_type"] == "session"
    assert attempt["participant_id"] == str(active.participant_id)
    assert attempt["schema_version"] == CSV_SCHEMA_VERSION
    metrics = json.loads(attempt["feedback_metrics_json"])
    assert metrics == [metric.model_dump(mode="json") for metric in session.feedback.metrics]
    assert metrics[0]["evidence_turns"]
    assert attempt["feedback_generation_source"] == "deterministic"
    assert attempt["pre_confidence"] == "2" and attempt["post_confidence"] == "5"
    assert attempt["pre_submitted_at"] and attempt["post_submitted_at"]
    assert attempt["roleplay_started_at"] and attempt["roleplay_completed_at"]
    assert json.loads(attempt["generation_source_counts_json"]) == {"scenario_opening": 1, "deterministic_roleplay": 1}
    assert json.loads(attempt["fallback_reason_counts_json"]) == {}
    assert json.loads(attempt["event_counts_json"])["questionnaire_post_submitted"] == 1
    assert idle_row["row_type"] == "participant"
    assert idle_row["participant_id"] == str(idle.participant_id)
    assert idle_row["enrolled_at"] and idle_row["consent_version"] and idle_row["eligibility_version"]
    assert idle_row["session_id"] == idle_row["turn_count"] == idle_row["feedback_metrics_json"] == ""
    assert str(excluded.participant_id) not in live

    # Export depends on durable records, not expiring/deleted conversation sessions.
    await repository.delete_session(session.id, active.id)
    assert (await build_research_csv(repository))[0] == live
    frozen, frozen_count, frozen_participants = await build_research_csv(repository, True)
    frozen_rows = list(csv.DictReader(io.StringIO(frozen)))
    assert frozen_count == count and frozen_participants == participants
    assert frozen_rows[0]["participant_id"] == "P0001"
    assert frozen_rows[0]["session_id"] == "P0001-S001"
    assert frozen_rows[1]["participant_id"] == "P0002"
    assert frozen_rows[1]["session_id"] == ""
    for private in ("PRIVATE_NAME", "PRIVATE_HASH", "PRIVATE_TAKEAWAY", "PRIVATE_EVENT_TEXT", "active@example.com", session.turns[-1].content):
        assert private not in live and private not in frozen
    for identifier in (active.id, active.participant_id, idle.participant_id, session.id):
        assert str(identifier) not in frozen
    assert (await build_research_csv(repository, True))[0] == frozen


@pytest.mark.asyncio
async def test_source_counts_distinguish_fallbacks_and_missing_legacy_metadata():
    repository = MemoryRepository()
    user = participant("sources@example.com")
    await repository.create_user(user)
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    session = Session(user_id=user.id)
    session.turns = [
        ConversationTurn(role=Role.ASSISTANT, content="private", generation=GenerationMetadata(source="template", fallback_reason="missing_api_key"), created_at=user.study_consent.accepted_at-timedelta(seconds=1)),
        ConversationTurn(role=Role.ASSISTANT, content="private", generation=GenerationMetadata(source="openai_roleplay")),
        ConversationTurn(role=Role.ASSISTANT, content="private", generation=GenerationMetadata(source="template", fallback_reason="roleplay_TimeoutError")),
        ConversationTurn(role=Role.ASSISTANT, content="private"),
    ]
    await service.save(session)
    record = (await repository.list_study_records(user.id))[0]
    assert record.generation_source_counts == {"openai_roleplay": 1, "template": 1, "unrecorded": 1}
    assert record.fallback_reason_counts == {"roleplay_TimeoutError": 1}
    legacy = StudyRecord(
        user_id=user.id, participant_id=user.participant_id, session_id=uuid4(),
        consent_version=user.study_consent.version, protocol_version=settings.study_protocol_version,
        enrolled_at=user.pilot_enrolled_at, session_created_at=utcnow(), last_activity_at=utcnow(),
        retention_expires_at=utcnow()+timedelta(days=1),
        feedback_metrics=[FeedbackMetric(name="clear request", score=0)],
    )
    await repository.save_study_record(legacy)
    old_protocol = legacy.model_copy(update={"id": uuid4(), "session_id": uuid4(), "protocol_version": "old-protocol"})
    await repository.save_study_record(old_protocol)
    content, count, _ = await build_research_csv(repository)
    rows = list(csv.DictReader(io.StringIO(content)))
    assert count == 2
    assert "old-protocol" not in content
    assert json.loads(rows[0]["fallback_reason_counts_json"]) == {"roleplay_TimeoutError": 1}
    assert rows[1]["generation_source_counts_json"] == ""
    assert rows[1]["fallback_reason_counts_json"] == ""
    assert json.loads(rows[1]["feedback_metrics_json"])[0]["score"] == 0


@pytest.mark.asyncio
async def test_empty_export_has_versioned_columns_and_no_invented_participants():
    content, count, participants = await build_research_csv(MemoryRepository())
    reader = csv.DictReader(io.StringIO(content))
    assert reader.fieldnames == CSV_FIELDS
    assert list(reader) == []
    assert count == participants == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("manual", [False, True])
async def test_completed_measurements_and_export_ignore_later_reflection(manual):
    repository = MemoryRepository()
    user = participant("completed-reflection@example.com")
    await repository.create_user(user)
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    session = await service.create_session(user.id)
    session, _, _ = await service.start_roleplay(session.id, user.id, "workload", Difficulty.INTERMEDIATE, pre_ratings={"confidence": 2, "anxiety": 6})
    if manual:
        await service.chat(session.id, user.id, "I am unsure what to say.")
        session = await service.set_roleplay_status(session.id, user.id, "finish")
    else:
        _, _, session = await service.chat(session.id, user.id, "I need the deadline moved to Friday because I have 12 hours of work.")
    assert (await repository.list_study_records(user.id))[0].turn_count == 3
    await service.submit_questionnaire(session.id, user.id, "post", {"confidence": 5, "realism": 6, "usefulness": 7}, post_token=session.post_questionnaire_token)
    before = (await repository.list_study_records(user.id))[0].model_dump(exclude={"updated_at", "id", "created_at"})
    original_export = (await build_research_csv(repository))[0]
    state = session.roleplay.model_dump()
    feedback = session.feedback.model_dump()
    for message in ["I feel better prepared now.", "I want to kill myself"]:
        reply, _, session = await service.chat(session.id, user.id, message)
        assert reply.content
        assert session.roleplay.model_dump() == state
        assert session.feedback.model_dump() == feedback
        assert (await repository.list_study_records(user.id))[0].model_dump(exclude={"updated_at", "id", "created_at"}) == before
        assert (await build_research_csv(repository))[0] == original_export
    assert reply.generation.source == "safety_response"
    assert len(session.turns) == 7
    # Restart/backfill uses the persisted boundary, not the later session timestamp.
    await service.backfill_active_study_records()
    assert (await build_research_csv(repository))[0] == original_export


@pytest.mark.asyncio
@pytest.mark.parametrize("paused", [False, True])
async def test_safety_still_interrupts_running_rehearsals_and_bounds_measurement(paused):
    repository = MemoryRepository()
    user = participant("interrupted-reflection@example.com")
    await repository.create_user(user)
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    session = await service.create_session(user.id)
    session, _, _ = await service.start_roleplay(session.id, user.id, "boundary", Difficulty.INTERMEDIATE, pre_skipped=True)
    if paused:
        await service.set_roleplay_status(session.id, user.id, "pause")
    reply, _, session = await service.chat(session.id, user.id, "I want to kill myself")
    assert reply.generation.source == "safety_response"
    assert session.roleplay.status == "interrupted"
    assert session.roleplay.completion_reason == "safety_interruption"
    assert session.roleplay.completed_at and session.roleplay.measurement_ended_at
    before = (await build_research_csv(repository))[0]
    await service.chat(session.id, user.id, "I am ready to reflect now.")
    assert (await build_research_csv(repository))[0] == before


@pytest.mark.asyncio
async def test_legacy_completion_excludes_later_reflection_without_losing_closing_reply():
    repository = MemoryRepository()
    user = participant("legacy-completed@example.com")
    await repository.create_user(user)
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    session = await service.create_session(user.id)
    session, _, _ = await service.start_roleplay(session.id, user.id, "workload", Difficulty.INTERMEDIATE, pre_skipped=True)
    _, _, session = await service.chat(session.id, user.id, "I need the deadline moved to Friday.")
    session.roleplay.measurement_ended_at = None
    await service.save(session)
    await service.close_post_questionnaire(session.id, user.id)
    before = (await build_research_csv(repository))[0]
    await service.chat(session.id, user.id, "A later reflection.")
    await service.chat(session.id, user.id, "I want to kill myself")
    assert (await repository.list_study_records(user.id))[0].turn_count == 3
    assert (await build_research_csv(repository))[0] == before
