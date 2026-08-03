from datetime import datetime
from uuid import UUID

from app.models.domain import Session, User, utcnow
from app.repositories.base import Repository


class MemoryRepository(Repository):
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}
        self.sessions: dict[UUID, Session] = {}
        self.tokens: dict[str, tuple[UUID, str, datetime]] = {}

    async def initialize(self) -> None: pass
    async def create_user(self, user: User) -> User:
        if await self.get_user_by_email(user.email):
            raise ValueError("duplicate email")
        self.users[user.id] = user
        return user
    async def get_user_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email), None)
    async def get_user(self, user_id: UUID) -> User | None: return self.users.get(user_id)
    async def delete_user(self, user_id: UUID) -> None:
        self.users.pop(user_id, None)
        self.sessions = {key: val for key, val in self.sessions.items() if val.user_id != user_id}
        await self.revoke_user_tokens(user_id)
    async def save_session(self, session: Session) -> Session:
        self.sessions[session.id] = session
        return session
    async def get_session(self, session_id: UUID, user_id: UUID) -> Session | None:
        session = self.sessions.get(session_id)
        return session if session and session.user_id == user_id and session.expires_at > utcnow() else None
    async def list_sessions(self, user_id: UUID) -> list[Session]:
        return sorted((s for s in self.sessions.values() if s.user_id == user_id), key=lambda s: s.updated_at, reverse=True)
    async def delete_session(self, session_id: UUID, user_id: UUID) -> bool:
        if await self.get_session(session_id, user_id):
            del self.sessions[session_id]
            return True
        return False
    async def store_refresh_token(self, token_id: str, user_id: UUID, digest: str, expires_at) -> None:
        self.tokens[token_id] = (user_id, digest, expires_at)
    async def rotate_refresh_token(self, token_id: str, digest: str) -> UUID | None:
        record = self.tokens.pop(token_id, None)
        if not record or record[1] != digest or record[2] <= utcnow(): return None
        return record[0]
    async def revoke_user_tokens(self, user_id: UUID) -> None:
        self.tokens = {key: val for key, val in self.tokens.items() if val[0] != user_id}

