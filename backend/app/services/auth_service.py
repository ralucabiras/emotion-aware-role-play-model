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
    async def update_profile(self, user: User, profile: dict[str, str]) -> User:
        for field in ("first_name", "last_name", "preferred_name", "country", "timezone"):
            if field in profile:
                setattr(user, field, profile[field].strip())
        if not user.first_name or not user.last_name or not user.timezone:
            raise ValueError("First name, last name, and timezone are required")
        return await self.repository.save_user(user)
    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not password_hash.verify(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")
        if password_hash.verify(new_password, user.password_hash):
            raise ValueError("New password must be different")
        user.password_hash = password_hash.hash(new_password)
        await self.repository.save_user(user)
        await self.repository.revoke_user_tokens(user.id)
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
