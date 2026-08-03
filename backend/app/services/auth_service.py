import hashlib
from datetime import timedelta
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.models.domain import User, utcnow
from app.repositories.base import Repository

password_hash = PasswordHash.recommended()


class AuthenticationError(ValueError): pass


class AuthService:
    def __init__(self, repository: Repository) -> None: self.repository = repository
    async def register(self, email: str, password: str, consent: bool) -> User:
        if not consent: raise ValueError("Privacy consent is required")
        user = User(email=email.strip().lower(), password_hash=password_hash.hash(password), consented_at=utcnow())
        return await self.repository.create_user(user)
    async def authenticate(self, email: str, password: str) -> User:
        user = await self.repository.get_user_by_email(email.strip().lower())
        if not user or not password_hash.verify(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        return user
    def access_token(self, user_id: UUID) -> str:
        now = utcnow()
        return jwt.encode({"sub": str(user_id), "type": "access", "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes)}, settings.jwt_secret, algorithm="HS256")
    async def refresh_token(self, user_id: UUID) -> str:
        now, token_id = utcnow(), str(uuid4())
        token = jwt.encode({"sub": str(user_id), "jti": token_id, "type": "refresh", "iat": now, "exp": now + timedelta(days=settings.refresh_token_days)}, settings.jwt_secret, algorithm="HS256")
        await self.repository.store_refresh_token(token_id, user_id, hashlib.sha256(token.encode()).hexdigest(), now + timedelta(days=settings.refresh_token_days))
        return token
    def decode_access(self, token: str) -> UUID:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            if payload.get("type") != "access": raise AuthenticationError
            return UUID(payload["sub"])
        except (jwt.PyJWTError, KeyError, ValueError) as exc: raise AuthenticationError from exc
    async def rotate(self, token: str) -> tuple[UUID, str]:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            if payload.get("type") != "refresh": raise AuthenticationError
            user_id = await self.repository.rotate_refresh_token(payload["jti"], hashlib.sha256(token.encode()).hexdigest())
            if not user_id: raise AuthenticationError
        except (jwt.PyJWTError, KeyError, ValueError) as exc: raise AuthenticationError from exc
        return user_id, await self.refresh_token(user_id)

