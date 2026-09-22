import time
from collections import defaultdict, deque
from dataclasses import dataclass

from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from app.core.config import Settings


@dataclass(frozen=True)
class RatePolicy:
    name: str
    limit: int
    window_seconds: int


class SecurityHeadersMiddleware:
    def __init__(self, app, production: bool) -> None:
        self.app, self.production = app, production

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def secure_send(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"permissions-policy", b"camera=(), microphone=(self), geolocation=()"),
                    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'"),
                    (b"cache-control", b"no-store"),
                ])
                if self.production:
                    headers.append((b"strict-transport-security", b"max-age=63072000; includeSubDomains"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, secure_send)


class RateLimitMiddleware:
    """Small single-instance limiter. A remote multi-instance pilot should use a shared gateway/Redis limiter."""

    EMAIL_PATHS = {"/api/auth/register", "/api/auth/resend-verification", "/api/auth/forgot-password"}
    AUTH_PATHS = {"/api/auth/login", "/api/auth/refresh", "/api/auth/verify-email", "/api/auth/reset-password"}
    MODEL_PATHS = {"/api/chat", "/api/affect/multimodal"}

    def __init__(self, app, settings: Settings) -> None:
        self.app, self.settings = app, settings
        self.events: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def policy(self, path: str, method: str) -> RatePolicy | None:
        if method not in {"POST", "PUT", "PATCH"}:
            return None
        if path in self.EMAIL_PATHS:
            return RatePolicy("email", self.settings.rate_limit_email_per_hour, 3600)
        if path in self.AUTH_PATHS:
            return RatePolicy("auth", self.settings.rate_limit_auth_per_minute, 60)
        if path == "/api/audio/transcriptions":
            return RatePolicy("transcription", self.settings.rate_limit_transcription_per_minute, 60)
        if path in self.MODEL_PATHS or path.endswith("/roleplay") or path.endswith("/roleplay/action"):
            return RatePolicy("model", self.settings.rate_limit_model_per_minute, 60)
        return None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.settings.rate_limit_enabled:
            return await self.app(scope, receive, send)
        policy = self.policy(scope.get("path", ""), scope.get("method", "GET"))
        if not policy:
            return await self.app(scope, receive, send)
        client = scope.get("client")
        identity = client[0] if client else "unknown"
        authorization = Headers(scope=scope).get("authorization")
        if authorization:
            identity = f"{identity}:{authorization[-24:]}"
        key, now = (identity, policy.name), time.monotonic()
        bucket = self.events[key]
        while bucket and bucket[0] <= now - policy.window_seconds:
            bucket.popleft()
        if len(bucket) >= policy.limit:
            retry_after = max(1, int(policy.window_seconds - (now - bucket[0])) + 1)
            response = JSONResponse(
                {"detail": "Too many requests. Please try again later."},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
            return await response(scope, receive, send)
        bucket.append(now)
        await self.app(scope, receive, send)
