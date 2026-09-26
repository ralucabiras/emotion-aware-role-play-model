"""Opt-in integration tests against a uniquely named real MongoDB database."""
import asyncio
import os
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.domain import Session, StudyRecord, User, utcnow
from app.repositories.mongo import ConcurrentSessionUpdateError, MongoRepository
from scripts.mongo_backup import backup_database, restore_database

MONGO_URI = os.getenv("TEST_MONGODB_URI")
pytestmark = [pytest.mark.mongo_integration, pytest.mark.skipif(not MONGO_URI, reason="Set TEST_MONGODB_URI to run real MongoDB tests")]

@pytest_asyncio.fixture
async def mongo_repository():
    repository = MongoRepository(MONGO_URI or "mongodb://localhost:27017", f"affectlab_integration_{uuid4().hex}")
    await repository.initialize()
    try:
        yield repository
    finally:
        await repository.client.drop_database(repository.db.name)
        await repository.client.close()

def make_user() -> User:
    return User(email=f"test-{uuid4().hex}@example.com", password_hash="not-a-real-hash", consented_at=utcnow())

def make_record(user: User, session: Session) -> StudyRecord:
    return StudyRecord(user_id=user.id, participant_id=user.participant_id, session_id=session.id, consent_version="2026.1", protocol_version="AL-FEAS-1.0", enrolled_at=utcnow(), session_created_at=session.created_at, last_activity_at=utcnow(), retention_expires_at=utcnow()+timedelta(days=365))

@pytest.mark.asyncio
async def test_data_persists_when_repository_client_restarts(mongo_repository):
    user = await mongo_repository.create_user(make_user())
    session = await mongo_repository.save_session(Session(user_id=user.id, title="Persistent session"))
    database = mongo_repository.db.name
    await mongo_repository.client.close()
    restarted = MongoRepository(MONGO_URI, database)
    await restarted.initialize()
    restored = await restarted.get_session(session.id, user.id)
    assert restored is not None and restored.title == "Persistent session"
    mongo_repository.client, mongo_repository.db = restarted.client, restarted.db

@pytest.mark.asyncio
async def test_ttl_index_and_logical_expiry_do_not_remove_research_record(mongo_repository):
    user = await mongo_repository.create_user(make_user())
    expired = await mongo_repository.save_session(Session(user_id=user.id, expires_at=utcnow()-timedelta(seconds=1)))
    await mongo_repository.save_study_record(make_record(user, expired))
    indexes = await mongo_repository.db.sessions.index_information()
    assert any(spec.get("expireAfterSeconds") == 0 and spec["key"] == [('expires_at', 1)] for spec in indexes.values())
    assert await mongo_repository.get_session(expired.id, user.id) is None
    assert len(await mongo_repository.list_study_records(user.id)) == 1

@pytest.mark.asyncio
async def test_account_deletion_cascades_across_personal_collections(mongo_repository):
    user = await mongo_repository.create_user(make_user())
    session = await mongo_repository.save_session(Session(user_id=user.id))
    await mongo_repository.save_study_record(make_record(user, session))
    expiry = utcnow()+timedelta(days=1)
    await mongo_repository.store_refresh_token("token", user.id, "digest", expiry)
    await mongo_repository.store_email_verification_token(user.id, "verify", expiry)
    await mongo_repository.store_password_reset_token(user.id, "reset", expiry)
    await mongo_repository.delete_user(user.id)
    for collection in ("sessions","study_records","refresh_tokens","email_verification_tokens","password_reset_tokens"):
        assert await mongo_repository.db[collection].count_documents({"user_id":user.id}) == 0
    assert await mongo_repository.db.users.count_documents({"id":user.id}) == 0

@pytest.mark.asyncio
async def test_concurrent_session_updates_reject_a_lost_update(mongo_repository):
    user = await mongo_repository.create_user(make_user())
    original = await mongo_repository.save_session(Session(user_id=user.id))
    first = await mongo_repository.get_session(original.id,user.id)
    second = await mongo_repository.get_session(original.id,user.id)
    assert first and second
    first.title, second.title = "First writer", "Second writer"
    results = await asyncio.gather(mongo_repository.save_session(first), mongo_repository.save_session(second), return_exceptions=True)
    assert sum(isinstance(result, ConcurrentSessionUpdateError) for result in results) == 1
    persisted = await mongo_repository.get_session(original.id,user.id)
    assert persisted and persisted.title in {"First writer","Second writer"}
    assert persisted.version == original.version + 1

@pytest.mark.asyncio
async def test_backup_can_be_restored_and_verified(mongo_repository, tmp_path):
    user = await mongo_repository.create_user(make_user())
    session = await mongo_repository.save_session(Session(user_id=user.id, title="Backup verification"))
    await mongo_repository.save_study_record(make_record(user, session))
    source_database = mongo_repository.db.name
    target_database = f"affectlab_{uuid4().hex[:20]}_restore_test"
    backup_path = tmp_path / "backup"
    manifest = await asyncio.to_thread(backup_database, MONGO_URI, source_database, backup_path)
    try:
        result = await asyncio.to_thread(restore_database, MONGO_URI, backup_path, target_database)
        assert result["verified"] is True
        assert result["collections"]["users"] == 1
        assert result["collections"]["sessions"] == 1
        assert result["collections"]["study_records"] == 1
        assert manifest["schema_version"] == "affectlab-mongodb-backup-v1"
    finally:
        await mongo_repository.client.drop_database(target_database)


@pytest.mark.asyncio
async def test_password_reset_rejection_preserves_link_and_concurrent_success_is_single_use(mongo_repository):
    import hashlib

    from app.services.auth_service import AuthenticationError, AuthService, password_hash

    user = make_user()
    user.password_hash = password_hash.hash("original-password")
    await mongo_repository.create_user(user)
    auth = AuthService(mongo_repository)
    digest = hashlib.sha256(b"reset-token").hexdigest()
    await mongo_repository.store_password_reset_token(user.id, digest, utcnow()+timedelta(minutes=10))
    with pytest.raises(ValueError, match="New password must be different"):
        await auth.reset_password("reset-token", "original-password")
    assert await mongo_repository.get_password_reset_user(digest) == user.id
    passwords = ["first-new-password", "second-new-password"]
    results = await asyncio.gather(*(auth.reset_password("reset-token", password) for password in passwords), return_exceptions=True)
    assert sum(result is None for result in results) == 1
    assert sum(isinstance(result, AuthenticationError) for result in results) == 1
    reloaded = await mongo_repository.get_user(user.id)
    assert password_hash.verify(passwords[results.index(None)], reloaded.password_hash)
    assert await mongo_repository.get_password_reset_user(digest) is None
    with pytest.raises(AuthenticationError):
        await auth.reset_password("reset-token", "third-new-password")


@pytest.mark.asyncio
async def test_enrolled_rehearsal_round_trip_and_restart(mongo_repository):
    from app.core.config import settings
    from app.models.domain import Difficulty, StudyConsentRecord, StudyEligibilityRecord
    from app.services.conversation_service import ConversationService
    from app.services.eligibility import eligibility_version
    from app.services.llm_service import TemplateResponseGenerator

    user = make_user()
    user.pilot_enrolled_at = utcnow()
    user.study_consent = StudyConsentRecord(version=settings.study_consent_version,
        protocol_version=settings.study_protocol_version, accepted_at=user.pilot_enrolled_at)
    user.study_eligibility = StudyEligibilityRecord(version=eligibility_version(),
        protocol_version=settings.study_protocol_version)
    await mongo_repository.create_user(user)
    service = ConversationService(mongo_repository, generator=TemplateResponseGenerator())
    session = await service.create_session(user.id)
    session, _, _ = await service.start_roleplay(session.id, user.id, "workload",
        Difficulty.INTERMEDIATE, pre_ratings={"confidence": 4, "anxiety": 4},
        attempt_purpose="required", required_task_id="workload")
    _, _, session = await service.chat(session.id, user.id,
        "I need the report deadline moved to Friday because I have 12 hours of work.")
    await service.submit_questionnaire(session.id, user.id, "post",
        {"confidence": 5, "realism": 4, "usefulness": 6}, post_token=session.post_questionnaire_token)
    restarted = MongoRepository(MONGO_URI, mongo_repository.db.name)
    try:
        await restarted.initialize()
        restored_user = await restarted.get_user(user.id)
        restored_session = await restarted.get_session(session.id, user.id)
        assert restored_user.study_consent.accepted_at.utcoffset() == timedelta(0)
        assert restored_session.roleplay.completed_at.utcoffset() == timedelta(0)
        await ConversationService(restarted, generator=TemplateResponseGenerator()).backfill_active_study_records()
        records = await restarted.list_study_records(user.id)
        assert len(records) == 1
        assert records[0].completion_reason == "success"
        assert records[0].questionnaires["post"].confidence == 5
        assert records[0].roleplay_completed_at >= records[0].roleplay_started_at
    finally:
        await restarted.client.close()
