import hashlib
import secrets
from datetime import timedelta
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.models.domain import User, utcnow
from app.repositories.base import Repository
from app.services.email_service import EmailService

password_hash = PasswordHash.recommended()


class AuthenticationError(ValueError): pass
class EmailNotVerifiedError(AuthenticationError): pass


class AuthService:
    def __init__(self, repository: Repository, email_service: EmailService | None = None) -> None:
        self.repository = repository
        self.email_service = email_service or EmailService()
    async def register(self, email: str, password: str, consent: bool, profile: dict | None = None) -> User:
        if not consent: raise ValueError("Privacy consent is required")
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash.hash(password),
            consented_at=utcnow(),
            **(profile or {}),
        )
        user = await self.repository.create_user(user)
        await self.send_verification(user)
        return user
    async def send_verification(self, user: User) -> None:
        if user.email_verified_at: return
        raw_token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(raw_token.encode()).hexdigest()
        await self.repository.store_email_verification_token(
            user.id,
            digest,
            utcnow() + timedelta(hours=settings.email_verification_hours),
        )
        await self.email_service.send_verification(user.email, user.preferred_name or user.first_name, raw_token)
    async def resend_verification(self, email: str) -> None:
        user = await self.repository.get_user_by_email(email.strip().lower())
        if user and not user.email_verified_at:
            await self.send_verification(user)
    async def verify_email(self, raw_token: str) -> User:
        digest = hashlib.sha256(raw_token.encode()).hexdigest()
        user_id = await self.repository.consume_email_verification_token(digest)
        if not user_id:
            raise AuthenticationError("Invalid or expired verification link")
        user = await self.repository.mark_email_verified(user_id)
        if not user:
            raise AuthenticationError("Invalid or expired verification link")
        return user
    async def authenticate(self, email: str, password: str) -> User:
        user = await self.repository.get_user_by_email(email.strip().lower())
        if not user or not password_hash.verify(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        if not user.email_verified_at:
            raise EmailNotVerifiedError("Email confirmation required")
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
