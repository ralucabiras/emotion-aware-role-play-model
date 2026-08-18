from uuid import UUID

from pymongo import ASCENDING, AsyncMongoClient
from pymongo.errors import DuplicateKeyError

from app.models.domain import Session, User, utcnow
from app.repositories.base import Repository


class MongoRepository(Repository):
    def __init__(self, uri: str, database: str) -> None:
        self.client = AsyncMongoClient(uri, uuidRepresentation="standard")
        self.db = self.client[database]

    async def initialize(self) -> None:
        await self.db.users.create_index("email", unique=True)
        await self.db.sessions.create_index("expires_at", expireAfterSeconds=0)
        await self.db.sessions.create_index([("user_id", ASCENDING), ("updated_at", -1)])
        await self.db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
        await self.db.email_verification_tokens.create_index("expires_at", expireAfterSeconds=0)
        await self.db.email_verification_tokens.create_index("user_id", unique=True)
        await self.db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
        await self.db.password_reset_tokens.create_index("user_id", unique=True)
    async def create_user(self, user: User) -> User:
        try: await self.db.users.insert_one(user.model_dump(mode="python"))
        except DuplicateKeyError as exc: raise ValueError("duplicate email") from exc
        return user
    async def get_user_by_email(self, email: str) -> User | None:
        doc = await self.db.users.find_one({"email": email})
        return User.model_validate(doc) if doc else None
    async def get_user(self, user_id: UUID) -> User | None:
        doc = await self.db.users.find_one({"id": user_id})
        return User.model_validate(doc) if doc else None
    async def save_user(self, user: User) -> User:
        await self.db.users.replace_one(
            {"id": user.id}, user.model_dump(mode="python"), upsert=False
        )
        return user
    async def delete_user(self, user_id: UUID) -> None:
        await self.db.users.delete_one({"id": user_id})
        await self.db.sessions.delete_many({"user_id": user_id})
        await self.db.refresh_tokens.delete_many({"user_id": user_id})
        await self.db.email_verification_tokens.delete_many({"user_id": user_id})
        await self.db.password_reset_tokens.delete_many({"user_id": user_id})
    async def save_session(self, session: Session) -> Session:
        await self.db.sessions.replace_one({"id": session.id}, session.model_dump(mode="python"), upsert=True)
        return session
    async def get_session(self, session_id: UUID, user_id: UUID) -> Session | None:
        doc = await self.db.sessions.find_one({"id": session_id, "user_id": user_id, "expires_at": {"$gt": utcnow()}})
        return Session.model_validate(doc) if doc else None
    async def list_sessions(self, user_id: UUID) -> list[Session]:
        docs = await self.db.sessions.find({"user_id": user_id, "expires_at": {"$gt": utcnow()}}).sort("updated_at", -1).to_list(None)
        return [Session.model_validate(doc) for doc in docs]
    async def delete_session(self, session_id: UUID, user_id: UUID) -> bool:
        return (await self.db.sessions.delete_one({"id": session_id, "user_id": user_id})).deleted_count == 1
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
    async def consume_password_reset_token(self, digest: str) -> UUID | None:
        doc = await self.db.password_reset_tokens.find_one_and_delete(
            {"digest": digest, "expires_at": {"$gt": utcnow()}}
        )
        return doc["user_id"] if doc else None
