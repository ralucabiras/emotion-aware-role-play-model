import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routes import set_refresh_cookie
from app.core.config import Settings, settings
from app.core.security import RateLimitMiddleware, SecurityHeadersMiddleware


def production_settings(**overrides):
    values = {
        "environment": "production",
        "jwt_secret": "a-unique-production-secret-with-more-than-32-bytes",
        "cors_allowed_origins": "https://pilot.example.org",
        "trusted_hosts": "pilot.example.org",
        "enforce_https": True,
        "rate_limit_enabled": True,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("secret", ["short", "secret", "replace-with-a-long-random-secret", "development-only-change-me-at-least-32-bytes"])
def test_production_rejects_default_or_weak_jwt_secret(secret):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        production_settings(jwt_secret=secret)


def test_production_requires_https_explicit_origins_hosts_and_rate_limits():
    with pytest.raises(ValidationError, match="HTTPS origins"):
        production_settings(cors_allowed_origins="*")
    with pytest.raises(ValidationError, match="TRUSTED_HOSTS"):
        production_settings(trusted_hosts="*")
    with pytest.raises(ValidationError, match="ENFORCE_HTTPS"):
        production_settings(enforce_https=False)
    with pytest.raises(ValidationError, match="RATE_LIMIT_ENABLED"):
        production_settings(rate_limit_enabled=False)


def test_refresh_cookie_is_secure_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    response = Response()
    set_refresh_cookie(response, "opaque-token")
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie


def test_security_headers_are_added():
    inner = FastAPI()
    inner.add_middleware(SecurityHeadersMiddleware, production=True)

    @inner.get("/")
    async def root():
        return {"ok": True}

    response = TestClient(inner).get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["strict-transport-security"].startswith("max-age=")
    assert response.headers["cache-control"] == "no-store"


def test_rate_limiter_returns_retry_after():
    limited = Settings(_env_file=None, rate_limit_enabled=True, rate_limit_auth_per_minute=2)
    inner = FastAPI()
    inner.add_middleware(RateLimitMiddleware, settings=limited)

    @inner.post("/api/auth/login")
    async def login():
        return {"ok": True}

    with TestClient(inner) as client:
        assert client.post("/api/auth/login").status_code == 200
        assert client.post("/api/auth/login").status_code == 200
        blocked = client.post("/api/auth/login")
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    assert blocked.json()["detail"] == "Too many requests. Please try again later."
