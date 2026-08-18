import base64
import binascii
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.container import (
    get_auth_service,
    get_conversation_service,
    get_multimodal_service,
    get_repository,
    get_transcription_service,
)
from app.models.domain import User
from app.schemas.chat import (
    AudioTranscriptionRequest,
    AudioTranscriptionResponse,
    AuthRequest,
    AuthResponse,
    ChatRequest,
    ChatResponse,
    CreateSessionResponse,
    EmailVerificationRequest,
    MultimodalAffectRequest,
    MultimodalAffectResponse,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    ProfileUpdateRequest,
    RegistrationResponse,
    ResendVerificationRequest,
    RolePlayActionRequest,
    SessionResponse,
    SessionSummary,
    StartRolePlayRequest,
    StartRolePlayResponse,
    UserResponse,
)
from app.services.auth_service import (
    AuthenticationError,
    AuthService,
    EmailNotVerifiedError,
)
from app.services.conversation_service import ConversationService, SessionNotFoundError
from app.services.email_service import EmailDeliveryError
from app.services.multimodal_service import (
    MultimodalAffectService,
    MultimodalInferenceUnavailable,
)
from app.services.roleplay_service import SCENARIOS
from app.services.transcription_service import InvalidAudio, TranscriptionService, TranscriptionUnavailable

router, bearer = APIRouter(prefix="/api"), HTTPBearer(auto_error=False)


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie("refresh_token", token, httponly=True, samesite="lax", secure=False, path="/api/auth", max_age=7 * 86400)


async def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), auth: AuthService = Depends(get_auth_service), repository=Depends(get_repository)) -> User:
    if not credentials: raise HTTPException(401, "Authentication required")
    try: user_id = auth.decode_access(credentials.credentials)
    except AuthenticationError: raise HTTPException(401, "Invalid or expired credentials") from None
    user = await repository.get_user(user_id)
    if not user: raise HTTPException(401, "Invalid or expired credentials")
    if not user.email_verified_at: raise HTTPException(403, "Email confirmation required")
    return user


@router.get("/health")
async def health(repository=Depends(get_repository)):
    return {"status": "ok", "persistence": type(repository).__name__}


@router.get("/models/info")
async def model_info(user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    multimodal = get_multimodal_service()
    transcription = get_transcription_service()
    return {"emotion_analyzer": getattr(service.analyzer, "version", "unknown"), "cognitive_analyzer": getattr(service.cognitive_analyzer, "version", "unknown"), "strategy_selector": "scored-rules-v2", "trained_model": multimodal.available, "multimodal_model": multimodal.version if multimodal.available else None, "multimodal_status": multimodal.status, "transcription_available": transcription.available, "transcription_model": transcription.model if transcription.available else None, "disclaimer": "Predictions are uncertain and are not diagnoses."}


@router.post("/audio/transcriptions", response_model=AudioTranscriptionResponse)
async def transcribe_audio(
    request: AudioTranscriptionRequest,
    user: User = Depends(current_user),
    transcription: TranscriptionService = Depends(get_transcription_service),
):
    del user
    try:
        audio = base64.b64decode(request.audio_wav_base64, validate=True)
        return await transcription.transcribe(audio)
    except binascii.Error:
        raise HTTPException(400, "Audio payload is not valid base64") from None
    except InvalidAudio as exc:
        raise HTTPException(400, str(exc)) from None
    except TranscriptionUnavailable as exc:
        raise HTTPException(503, str(exc)) from None


@router.post("/affect/multimodal", response_model=MultimodalAffectResponse)
async def multimodal_affect(
    request: MultimodalAffectRequest,
    user: User = Depends(current_user),
    conversations: ConversationService = Depends(get_conversation_service),
    multimodal: MultimodalAffectService = Depends(get_multimodal_service),
):
    try:
        session = await conversations.get_session(request.session_id, user.id)
        audio = base64.b64decode(request.audio_wav_base64, validate=True)
        return await multimodal.analyze(session, request.message, audio)
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found") from None
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(400, str(exc)) from None
    except MultimodalInferenceUnavailable as exc:
        raise HTTPException(503, str(exc)) from None


async def auth_response(user: User, response: Response, auth: AuthService) -> AuthResponse:
    set_refresh_cookie(response, await auth.refresh_token(user.id))
    return AuthResponse(access_token=auth.access_token(user.id), user=user_response(user))


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        preferred_name=user.preferred_name,
        country=user.country,
        timezone=user.timezone,
        email_verified=bool(user.email_verified_at),
    )


@router.post("/auth/register", response_model=RegistrationResponse, status_code=202)
async def register(request: AuthRequest, response: Response, auth: AuthService = Depends(get_auth_service)):
    profile = request.model_dump(
        include={"first_name", "last_name", "preferred_name", "country", "timezone"}
    )
    try: user = await auth.register(str(request.email), request.password, request.consent, profile)
    except ValueError as exc:
        detail = "An account with this email already exists" if "duplicate" in str(exc) else str(exc)
        raise HTTPException(409 if "duplicate" in str(exc) else 400, detail) from None
    except EmailDeliveryError:
        return RegistrationResponse(
            message="Account created, but email delivery is temporarily unavailable. Use resend shortly.",
            email=request.email,
        )
    return RegistrationResponse(message="Check your email to confirm your account", email=user.email)


@router.post("/auth/login", response_model=AuthResponse)
async def login(request: AuthRequest, response: Response, auth: AuthService = Depends(get_auth_service)):
    try: user = await auth.authenticate(str(request.email), request.password)
    except EmailNotVerifiedError: raise HTTPException(403, "Email confirmation required") from None
    except AuthenticationError: raise HTTPException(401, "Invalid email or password") from None
    return await auth_response(user, response, auth)


@router.post("/auth/verify-email")
async def verify_email(request: EmailVerificationRequest, auth: AuthService = Depends(get_auth_service)):
    try: await auth.verify_email(request.token)
    except AuthenticationError as exc: raise HTTPException(400, str(exc)) from None
    return {"message": "Email confirmed. You can now sign in."}


@router.post("/auth/resend-verification", status_code=202)
async def resend_verification(request: ResendVerificationRequest, auth: AuthService = Depends(get_auth_service)):
    try: await auth.resend_verification(str(request.email))
    except EmailDeliveryError: pass
    return {"message": "If the account exists and is unverified, a confirmation email has been sent."}


@router.post("/auth/forgot-password", status_code=202)
async def forgot_password(
    request: PasswordResetRequest, auth: AuthService = Depends(get_auth_service)
):
    try:
        await auth.request_password_reset(str(request.email))
    except EmailDeliveryError:
        pass
    return {"message": "If an eligible account exists, a password reset link has been sent."}


@router.post("/auth/reset-password", status_code=204)
async def reset_password(
    request: PasswordResetConfirmRequest,
    response: Response,
    auth: AuthService = Depends(get_auth_service),
):
    try:
        await auth.reset_password(request.token, request.new_password)
    except AuthenticationError as exc:
        raise HTTPException(400, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    response.delete_cookie("refresh_token", path="/api/auth")


@router.post("/auth/refresh", response_model=AuthResponse)
async def refresh(response: Response, refresh_token: str | None = Cookie(None), auth: AuthService = Depends(get_auth_service), repository=Depends(get_repository)):
    if not refresh_token: raise HTTPException(401, "Refresh token required")
    try: user_id, replacement = await auth.rotate(refresh_token)
    except AuthenticationError: raise HTTPException(401, "Invalid or expired credentials") from None
    user = await repository.get_user(user_id)
    if not user: raise HTTPException(401, "Invalid or expired credentials")
    set_refresh_cookie(response, replacement)
    if not user.email_verified_at: raise HTTPException(403, "Email confirmation required")
    return AuthResponse(access_token=auth.access_token(user.id), user=user_response(user))


@router.post("/auth/logout", status_code=204)
async def logout(response: Response, user: User = Depends(current_user), repository=Depends(get_repository)):
    await repository.revoke_user_tokens(user.id); response.delete_cookie("refresh_token", path="/api/auth")


@router.get("/auth/me", response_model=UserResponse)
async def me(user: User = Depends(current_user)): return user_response(user)


@router.patch("/auth/me", response_model=UserResponse)
async def update_me(
    request: ProfileUpdateRequest,
    user: User = Depends(current_user),
    auth: AuthService = Depends(get_auth_service),
):
    try:
        updated = await auth.update_profile(user, request.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    return user_response(updated)


@router.post("/auth/change-password", status_code=204)
async def change_password(
    request: PasswordChangeRequest,
    response: Response,
    user: User = Depends(current_user),
    auth: AuthService = Depends(get_auth_service),
):
    try:
        await auth.change_password(user, request.current_password, request.new_password)
    except AuthenticationError:
        raise HTTPException(400, "Current password is incorrect") from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    response.delete_cookie("refresh_token", path="/api/auth")


@router.delete("/auth/me", status_code=204)
async def delete_account(response: Response, user: User = Depends(current_user), repository=Depends(get_repository)):
    await repository.delete_user(user.id); response.delete_cookie("refresh_token", path="/api/auth")


@router.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session(user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    session = await service.create_session(user.id)
    return CreateSessionResponse(session_id=session.id, emotion_state=session.emotion_state)


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    return [SessionSummary(session_id=s.id, updated_at=s.updated_at.isoformat(), turn_count=len(s.turns), roleplay=s.roleplay) for s in await service.list_sessions(user.id)]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    try: session = await service.get_session(session_id, user.id)
    except SessionNotFoundError: raise HTTPException(404, "Session not found") from None
    return SessionResponse(session_id=session.id, turns=session.turns, emotion_state=session.emotion_state, roleplay=session.roleplay, feedback=session.feedback)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: UUID, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    try: await service.delete_session(session_id, user.id)
    except SessionNotFoundError: raise HTTPException(404, "Session not found") from None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    try: turn, decision, session = await service.chat(request.session_id, user.id, request.message)
    except SessionNotFoundError: raise HTTPException(404, "Session not found") from None
    except ValueError as exc: raise HTTPException(409, str(exc)) from None
    return ChatResponse(turn=turn, decision=decision, roleplay=session.roleplay, feedback=session.feedback)


@router.get("/roleplay/scenarios")
async def list_scenarios(user: User = Depends(current_user)): return list(SCENARIOS.values())


@router.post("/sessions/{session_id}/roleplay", response_model=StartRolePlayResponse)
async def start_roleplay(session_id: UUID, request: StartRolePlayRequest, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    try: state, scenario, turn = await service.start_roleplay(session_id, user.id, request.scenario_id, request.difficulty)
    except SessionNotFoundError: raise HTTPException(404, "Session not found") from None
    except KeyError: raise HTTPException(404, "Scenario not found") from None
    return StartRolePlayResponse(state=state, scenario=scenario, opening_turn=turn)


@router.post("/sessions/{session_id}/roleplay/action", response_model=SessionResponse)
async def roleplay_action(session_id: UUID, request: RolePlayActionRequest, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    try: session = await service.set_roleplay_status(session_id, user.id, request.action)
    except SessionNotFoundError: raise HTTPException(404, "Session not found") from None
    except ValueError as exc: raise HTTPException(409, str(exc)) from None
    return SessionResponse(session_id=session.id, turns=session.turns, emotion_state=session.emotion_state, roleplay=session.roleplay, feedback=session.feedback)


@router.get("/sessions/{session_id}/feedback")
async def get_feedback(session_id: UUID, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    session = await service.get_session(session_id, user.id)
    if not session.feedback: raise HTTPException(404, "Feedback not available")
    return session.feedback
