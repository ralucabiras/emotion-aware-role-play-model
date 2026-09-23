from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.core.container import conversation_service, repository
from app.core.security import RateLimitMiddleware, SecurityHeadersMiddleware
from app.models.domain import PracticeGoal, User, utcnow
from app.repositories.mongo import ConcurrentSessionUpdateError
from app.services.auth_service import password_hash


@asynccontextmanager
async def lifespan(app: FastAPI):
    await repository.initialize()
    if settings.offline_demo_mode:
        demo = await repository.get_user_by_email(settings.offline_demo_email)
        if not demo:
            await repository.create_user(User(
                email=settings.offline_demo_email,
                password_hash=password_hash.hash(settings.offline_demo_password),
                consented_at=utcnow(),
                email_verified_at=utcnow(),
                first_name="Demo",
                last_name="Participant",
                preferred_name="Demo",
                country="Romania",
                timezone="Europe/Bucharest",
                practice_goals=[PracticeGoal.CLEAR_REQUESTS, PracticeGoal.ASSERTIVENESS],
                onboarding_completed_at=utcnow(),
                onboarding_version=settings.onboarding_version,
            ))
    await conversation_service.backfill_active_study_records()
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)


@app.exception_handler(ConcurrentSessionUpdateError)
async def concurrent_session_update_handler(
    request: Request, exc: ConcurrentSessionUpdateError
) -> JSONResponse:
    del request, exc
    return JSONResponse(
        status_code=409,
        content={
            "detail": (
                "This session changed in another browser or tab. "
                "Reload the session, review the latest changes, and try again."
            ),
            "code": "session_update_conflict",
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RateLimitMiddleware, settings=settings)
app.add_middleware(SecurityHeadersMiddleware, production=settings.production)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
if settings.enforce_https:
    app.add_middleware(HTTPSRedirectMiddleware)
app.include_router(router)
