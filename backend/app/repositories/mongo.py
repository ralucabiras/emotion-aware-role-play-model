from datetime import timedelta
from uuid import UUID

from pymongo import ASCENDING, AsyncMongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.models.domain import FrozenStudyExport, Session, StudyLifecycle, StudyRecord, User, utcnow
from app.repositories.base import Repository, RepositoryIndexesNotReadyError


class ConcurrentSessionUpdateError(RuntimeError):
    """Raised instead of silently overwriting a concurrently updated session."""


class MongoRepository(Repository):
    REQUIRED_INDEXES = {
        "users": {"email_1"},
        "sessions": {"id_1", "expires_at_1", "user_id_1_updated_at_-1"},
        "study_records": {
            "session_id_1",
            "user_id_1_last_activity_at_-1",
            "retention_expires_at_1",
        },
        "study_lifecycle": {"protocol_version_1"},
        "frozen_study_exports": {"id_1", "protocol_version_1"},
        "refresh_tokens": {"expires_at_1"},
        "email_verification_tokens": {"expires_at_1", "user_id_1"},
        "password_reset_tokens": {"expires_at_1", "user_id_1"},
    }

    def __init__(self, uri: str, database: str) -> None:
        # BSON stores UTC instants; decode them with timezone information so
        # persisted dates remain comparable with newly created UTC timestamps.
        self.client = AsyncMongoClient(uri, uuidRepresentation="standard", tz_aware=True)
        self.db = self.client[database]
        self._initialized = False

    async def initialize(self) -> None:
        await self.db.users.create_index("email", unique=True)
        await self.db.sessions.create_index("id", unique=True)
        await self.db.sessions.create_index("expires_at", expireAfterSeconds=0)
        await self.db.sessions.create_index([("user_id", ASCENDING), ("updated_at", -1)])
        await self.db.study_records.create_index("session_id", unique=True)
        await self.db.study_records.create_index([("user_id", ASCENDING), ("last_activity_at", -1)])
        await self.db.study_records.create_index("retention_expires_at", expireAfterSeconds=0)
        await self.db.study_lifecycle.create_index("protocol_version", unique=True)
        await self.db.frozen_study_exports.create_index("id", unique=True)
        await self.db.frozen_study_exports.create_index("protocol_version", unique=True)
        await self.db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
        await self.db.email_verification_tokens.create_index("expires_at", expireAfterSeconds=0)
        await self.db.email_verification_tokens.create_index("user_id", unique=True)
        await self.db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
        await self.db.password_reset_tokens.create_index("user_id", unique=True)
        self._initialized = True
    async def check_readiness(self) -> None:
        await self.db.command("ping")
        if not self._initialized:
            raise RuntimeError("Repository initialization has not completed")
        for collection_name, required in self.REQUIRED_INDEXES.items():
            indexes = await self.db[collection_name].index_information()
            if not required.issubset(indexes):
                raise RepositoryIndexesNotReadyError(
                    f"Required indexes are missing for {collection_name}"
                )
    async def create_user(self, user: User) -> User:
        try: await self.db.users.insert_one(user.model_dump(mode="python"))
        except DuplicateKeyError as exc: raise ValueError("duplicate email") from exc
        return user
    async def get_user_by_email(self, email: str) -> User | None:
        doc = await self.db.users.find_one({"email": email})
        if not doc: return None
        user = User.model_validate(doc)
        if "participant_id" not in doc:
            await self.save_user(user)
        return user
    async def get_user(self, user_id: UUID) -> User | None:
        doc = await self.db.users.find_one({"id": user_id})
        if not doc: return None
        user = User.model_validate(doc)
        if "participant_id" not in doc:
            await self.save_user(user)
        return user
    async def list_users(self) -> list[User]:
        return [User.model_validate(doc) async for doc in self.db.users.find({})]
    async def save_user(self, user: User) -> User:
        await self.db.users.replace_one(
            {"id": user.id}, user.model_dump(mode="python"), upsert=False
        )
        return user
    async def delete_user(self, user_id: UUID) -> None:
        await self.db.users.delete_one({"id": user_id})
        await self.db.sessions.delete_many({"user_id": user_id})
        await self.db.study_records.delete_many({"user_id": user_id})
        await self.db.refresh_tokens.delete_many({"user_id": user_id})
        await self.db.email_verification_tokens.delete_many({"user_id": user_id})
        await self.db.password_reset_tokens.delete_many({"user_id": user_id})
    async def save_session(self, session: Session) -> Session:
        expected_version = session.version
        next_version = expected_version + 1
        document = session.model_dump(mode="python")
        document["version"] = next_version
        if expected_version == 0:
            result = await self.db.sessions.replace_one(
                {"id": session.id, "$or": [{"version": 0}, {"version": {"$exists": False}}]},
                document,
                upsert=False,
            )
            if result.matched_count == 0:
                try:
                    await self.db.sessions.insert_one(document)
                except DuplicateKeyError as exc:
                    raise ConcurrentSessionUpdateError("Session was updated by another request") from exc
        else:
            result = await self.db.sessions.replace_one(
                {"id": session.id, "version": expected_version}, document, upsert=False
            )
            if result.matched_count == 0:
                raise ConcurrentSessionUpdateError("Session was updated by another request")
        session.version = next_version
        return session
    async def get_session(self, session_id: UUID, user_id: UUID) -> Session | None:
        doc = await self.db.sessions.find_one({"id": session_id, "user_id": user_id, "expires_at": {"$gt": utcnow()}})
        return Session.model_validate(doc) if doc else None
    async def list_sessions(self, user_id: UUID) -> list[Session]:
        docs = await self.db.sessions.find({"user_id": user_id, "expires_at": {"$gt": utcnow()}}).sort("updated_at", -1).to_list(None)
        return [Session.model_validate(doc) for doc in docs]
    async def delete_session(self, session_id: UUID, user_id: UUID) -> bool:
        return (await self.db.sessions.delete_one({"id": session_id, "user_id": user_id})).deleted_count == 1
    async def save_study_record(self, record: StudyRecord) -> StudyRecord:
        document = record.model_dump(mode="python")
        record_id, created_at = document.pop("id"), document.pop("created_at")
        await self.db.study_records.update_one(
            {"session_id": record.session_id},
            {"$set": document, "$setOnInsert": {"id": record_id, "created_at": created_at}},
            upsert=True,
        )
        return record
    async def list_study_records(self, user_id: UUID | None = None) -> list[StudyRecord]:
        query = {"retention_expires_at": {"$gt": utcnow()}}
        if user_id is not None:
            query["user_id"] = user_id
        docs = await self.db.study_records.find(query).sort("last_activity_at", -1).to_list(None)
        return [StudyRecord.model_validate(doc) for doc in docs]
    async def delete_study_records(self, user_id: UUID) -> int:
        return (await self.db.study_records.delete_many({"user_id": user_id})).deleted_count
    async def get_study_lifecycle(self, protocol_version: str) -> StudyLifecycle | None:
        doc = await self.db.study_lifecycle.find_one({"protocol_version": protocol_version})
        return StudyLifecycle.model_validate(doc) if doc else None
    async def save_study_lifecycle(self, lifecycle: StudyLifecycle) -> StudyLifecycle:
        await self.db.study_lifecycle.replace_one(
            {"protocol_version": lifecycle.protocol_version},
            lifecycle.model_dump(mode="python"),
            upsert=True,
        )
        return lifecycle
    async def save_frozen_export(self, export: FrozenStudyExport) -> FrozenStudyExport:
        await self.db.frozen_study_exports.insert_one(export.model_dump(mode="python"))
        return export
    async def get_frozen_export(self, export_id: UUID) -> FrozenStudyExport | None:
        doc = await self.db.frozen_study_exports.find_one({"id": export_id})
        return FrozenStudyExport.model_validate(doc) if doc else None
    async def begin_dataset_freeze(self, protocol_version: str, token: UUID) -> StudyLifecycle | None:
        now = utcnow()
        stale_before = now - timedelta(hours=1)
        doc = await self.db.study_lifecycle.find_one_and_update(
            {
                "protocol_version": protocol_version,
                "dataset_frozen_at": None,
                "$or": [
                    {"freeze_token": None},
                    {"freeze_token": {"$exists": False}},
                    {"freeze_started_at": {"$lte": stale_before}},
                ],
            },
            {"$set": {"freeze_token": token, "freeze_started_at": now, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if doc:
            # A worker may have died after writing an export but before publishing
            # it on the lifecycle. Once its lease is reclaimed, that unreachable
            # export is safe to remove before rebuilding it.
            await self.db.frozen_study_exports.delete_many({"protocol_version": protocol_version})
        return StudyLifecycle.model_validate(doc) if doc else None
    async def complete_dataset_freeze(self, export: FrozenStudyExport, token: UUID) -> StudyLifecycle:
        try:
            async with await self.client.start_session() as session:
                async with session.start_transaction():
                    await self._write_completed_freeze(export, token, session=session)
        except OperationFailure as exc:
            if exc.code != 20 and "Transaction numbers are only allowed" not in str(exc):
                raise
            # Standalone MongoDB deployments do not support transactions. The
            # lifecycle claim fences concurrent freezes; begin_dataset_freeze
            # removes an unreachable export left by a crashed worker.
            try:
                await self._write_completed_freeze(export, token)
            except Exception:
                await self.db.frozen_study_exports.delete_one({"id": export.id})
                raise
        lifecycle = await self.get_study_lifecycle(export.protocol_version)
        if lifecycle is None:
            raise RuntimeError("Dataset lifecycle disappeared after freeze")
        return lifecycle
    async def _write_completed_freeze(self, export: FrozenStudyExport, token: UUID, session=None) -> None:
        await self.db.frozen_study_exports.insert_one(
            export.model_dump(mode="python"), session=session
        )
        result = await self.db.study_lifecycle.update_one(
            {
                "protocol_version": export.protocol_version,
                "freeze_token": token,
                "dataset_frozen_at": None,
            },
            {"$set": {
                "dataset_frozen_at": export.created_at,
                "frozen_export_id": export.id,
                "freeze_token": None,
                "freeze_started_at": None,
                "updated_at": export.created_at,
            }},
            session=session,
        )
        if result.modified_count != 1:
            raise RuntimeError("Dataset freeze lock was lost")
    async def abort_dataset_freeze(self, protocol_version: str, token: UUID) -> None:
        await self.db.study_lifecycle.update_one(
            {"protocol_version": protocol_version, "freeze_token": token, "dataset_frozen_at": None},
            {"$set": {"freeze_token": None, "freeze_started_at": None, "updated_at": utcnow()}},
        )
    async def store_refresh_token(self, token_id: str, user_id: UUID, digest: str, expires_at) -> None:
        await self.db.refresh_tokens.insert_one({"token_id": token_id, "user_id": user_id, "digest": digest, "expires_at": expires_at})
    async def rotate_refresh_token(self, token_id: str, digest: str) -> UUID | None:
        doc = await self.db.refresh_tokens.find_one_and_delete({"token_id": token_id, "digest": digest, "expires_at": {"$gt": utcnow()}})
        return doc["user_id"] if doc else None
    async def revoke_user_tokens(self, user_id: UUID) -> None:
        await self.db.refresh_tokens.delete_many({"user_id": user_id})
    async def store_email_verification_token(self, user_id: UUID, digest: str, expires_at) -> None:
        await self.db.email_verification_tokens.replace_one(
            {"user_id": user_id},
            {"user_id": user_id, "digest": digest, "expires_at": expires_at},
            upsert=True,
        )
    async def consume_email_verification_token(self, digest: str) -> UUID | None:
        # Keep the record until its TTL expires so repeated browser requests are
        # idempotent. React StrictMode and mail scanners may open the same link
        # more than once; repeating verification grants no additional access.
        doc = await self.db.email_verification_tokens.find_one(
            {"digest": digest, "expires_at": {"$gt": utcnow()}}
        )
        return doc["user_id"] if doc else None
    async def mark_email_verified(self, user_id: UUID) -> User | None:
        await self.db.users.update_one(
            {"id": user_id}, {"$set": {"email_verified_at": utcnow()}}
        )
        return await self.get_user(user_id)
    async def store_password_reset_token(self, user_id: UUID, digest: str, expires_at) -> None:
        await self.db.password_reset_tokens.replace_one(
            {"user_id": user_id},
            {"user_id": user_id, "digest": digest, "expires_at": expires_at},
            upsert=True,
        )
    async def get_password_reset_user(self, digest: str) -> UUID | None:
        doc = await self.db.password_reset_tokens.find_one(
            {"digest": digest, "expires_at": {"$gt": utcnow()}}
        )
        return doc["user_id"] if doc else None
    async def consume_password_reset_token(self, digest: str) -> UUID | None:
        doc = await self.db.password_reset_tokens.find_one_and_delete(
            {"digest": digest, "expires_at": {"$gt": utcnow()}}
        )
        return doc["user_id"] if doc else None
