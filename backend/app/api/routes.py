import base64
import binascii
import csv
import hmac
import io
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.container import (
    get_auth_service,
    get_conversation_service,
    get_multimodal_service,
    get_repository,
    get_transcription_service,
)
from app.models.domain import Difficulty, RolePlayScenario, StudyConsentRecord, User, utcnow
from app.schemas.chat import (
    AudioTranscriptionRequest,
    AudioTranscriptionResponse,
    AuthRequest,
    AuthResponse,
    ChatRequest,
    ChatResponse,
    CreateSessionResponse,
    CustomScenarioRequest,
    EmailVerificationRequest,
    MultimodalAffectRequest,
    MultimodalAffectResponse,
    OnboardingRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PilotEnrollmentRequest,
    ProfileUpdateRequest,
    RegistrationResponse,
    ResendVerificationRequest,
    RewindResponse,
    RolePlayActionRequest,
    SessionResponse,
    SessionSummary,
    SessionTitleRequest,
    StartRolePlayRequest,
    StartRolePlayResponse,
    StudyInformationResponse,
    StudyQuestionnaireRequest,
    StudyQuestionnaireResponse,
    TakeawayRequest,
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


def is_researcher(email: str) -> bool:
    allowed = {item.strip().lower() for item in settings.researcher_emails.split(",") if item.strip()}
    return email.strip().lower() in allowed


def has_current_study_consent(user: User) -> bool:
    return bool(
        user.pilot_enrolled_at
        and user.study_consent
        and user.study_consent.version == settings.study_consent_version
    )


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


async def researcher_user(user: User = Depends(current_user)) -> User:
    if not is_researcher(user.email): raise HTTPException(403, "Researcher access required")
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
        practice_goals=user.practice_goals,
        onboarding_completed=bool(user.onboarding_completed_at),
        onboarding_version=user.onboarding_version,
        researcher=is_researcher(user.email),
        pilot_enrolled=has_current_study_consent(user),
        study_consent_version=user.study_consent.version if user.study_consent else None,
        study_consented_at=user.study_consent.accepted_at.isoformat() if user.study_consent else None,
        participant_id=user.participant_id,
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


@router.put("/auth/onboarding", response_model=UserResponse)
async def complete_onboarding(
    request: OnboardingRequest,
    user: User = Depends(current_user),
    auth: AuthService = Depends(get_auth_service),
):
    try:
        updated = await auth.complete_onboarding(user, request.practice_goals)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    return user_response(updated)


@router.get("/auth/research-export")
async def research_export(
    user: User = Depends(current_user), repository=Depends(get_repository)
):
    sessions = await repository.list_sessions(user.id)
    return {
        "schema_version": "affectlab-research-export-v1",
        "participant_id": str(user.participant_id),
        "account_privacy_acceptance": {"version": user.consent_version, "accepted_at": user.consented_at},
        "study_consent": user.study_consent.model_dump(mode="json") if user.study_consent else None,
        "practice_goals": [goal.value for goal in user.practice_goals],
        "contains_conversation_text": False,
        "sessions": [
            {
                "session_id": str(session.id),
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "turn_count": len(session.turns),
                "roleplay": session.roleplay.model_dump(mode="json") if session.roleplay else None,
                "feedback_metrics": [
                    metric.model_dump(mode="json") for metric in session.feedback.metrics
                ] if session.feedback else [],
                "questionnaires": {
                    phase: answer.model_dump(mode="json")
                    for phase, answer in session.questionnaires.items()
                },
                "events": [event.model_dump(mode="json") for event in session.research_events],
            }
            for session in sessions
        ],
    }


@router.get("/research/study-information", response_model=StudyInformationResponse)
async def study_information(user: User = Depends(current_user)):
    return StudyInformationResponse(
        version=settings.study_consent_version,
        study_label=settings.pilot_study_label,
        title="Participant information sheet",
        summary=("AffectLab is a dissertation study of whether emotion-aware reflection and adaptive role-play can support practice for difficult conversations. Taking part is voluntary and is separate from holding an AffectLab account."),
        data_collected=[
            "A pseudonymous participant identifier and study-consent record.",
            "Questionnaire ratings, interaction events, scenario choices, completion data, and feedback metrics.",
            "Conversation text in active application sessions; researcher dashboard and CSV exports exclude this text.",
            "Profile and account data required to operate and secure the application; these are not included in pseudonymous study exports.",
        ],
        processors=[
            "MongoDB stores account, session, and consent records in the configured local database.",
            "When OpenAI features are configured, session context may be sent to OpenAI to generate responses, phrase feedback, moderate content, or transcribe optional speech.",
            "Email delivery uses the configured SMTP provider for account messages.",
        ],
        audio_and_transcripts=[
            "Voice input is optional and requires an explicit action for each recording.",
            "Audio may be sent to OpenAI for transcription and processed in memory by the local research model.",
            "AffectLab does not persist raw audio. A transcript you approve can become part of the conversation session.",
        ],
        retention=settings.study_retention_period,
        risks_and_limitations=[
            "Discussing difficult situations may feel uncomfortable; you may pause or stop at any time.",
            "Emotion estimates and generated replies can be inaccurate, biased, repetitive, or inappropriate.",
            "AffectLab is not therapy, diagnosis, medical advice, or an emergency service.",
            "The prototype cannot guarantee confidentiality beyond the safeguards described here.",
        ],
        withdrawal=[
            "Participation is voluntary. Declining does not prevent you from using your account outside the pilot.",
            "You may stop study activities at any time without giving a reason.",
            f"To request withdrawal, contact {settings.study_researcher_email}. Account deletion also removes active account and session data.",
            "The researcher will explain whether data already irreversibly anonymised or included in completed aggregate analysis can still be removed.",
        ],
        researcher={"name": settings.study_researcher_name, "email": settings.study_researcher_email},
        supervisor={"name": settings.study_supervisor_name, "email": settings.study_supervisor_email},
        institution=settings.study_institution,
    )


@router.post("/research/enroll", response_model=UserResponse)
async def enroll_in_pilot(
    request: PilotEnrollmentRequest,
    user: User = Depends(current_user),
    repository=Depends(get_repository),
):
    if not settings.pilot_access_code:
        raise HTTPException(503, "Pilot enrollment is not configured")
    if not hmac.compare_digest(request.access_code, settings.pilot_access_code):
        raise HTTPException(400, "The pilot access code is not valid")
    if request.consent_version != settings.study_consent_version:
        raise HTTPException(409, "The participant information has changed. Review the current version before consenting.")
    if not all((request.information_sheet_read, request.research_participation_accepted, request.data_processing_accepted)):
        raise HTTPException(400, "All study consent confirmations are required")
    if not user.pilot_enrolled_at:
        user.pilot_enrolled_at = utcnow()
    user.study_consent = StudyConsentRecord(
        version=settings.study_consent_version,
        information_sheet_read=request.information_sheet_read,
        research_participation_accepted=request.research_participation_accepted,
        data_processing_accepted=request.data_processing_accepted,
    )
    await repository.save_user(user)
    return user_response(user)


async def pilot_dataset(repository):
    users = [user for user in await repository.list_users() if has_current_study_consent(user)]
    records = []
    metric_values: dict[str, list[float]] = defaultdict(list)
    scenarios: dict[str, int] = defaultdict(int)
    difficulties: dict[str, int] = defaultdict(int)
    questionnaires: dict[str, list[float]] = defaultdict(list)
    generation_sources: dict[str, int] = defaultdict(int)
    total_sessions = completed = 0
    for user in users:
        sessions = await repository.list_sessions(user.id)
        total_sessions += len(sessions)
        user_completed = sum(bool(session.feedback) for session in sessions)
        completed += user_completed
        last_active = max((session.updated_at for session in sessions), default=user.pilot_enrolled_at)
        records.append({
            "participant_id": str(user.participant_id),
            "enrolled_at": user.pilot_enrolled_at,
            "last_active_at": last_active,
            "sessions": len(sessions),
            "completed_rehearsals": user_completed,
            "pre_questionnaires": sum("pre" in session.questionnaires for session in sessions),
            "post_questionnaires": sum("post" in session.questionnaires for session in sessions),
        })
        for session in sessions:
            if session.roleplay:
                scenarios[session.roleplay.scenario_id] += int(bool(session.feedback))
                difficulties[session.roleplay.difficulty_level.value] += int(bool(session.feedback))
            if session.feedback:
                generation_sources[session.feedback.generation_source] += 1
                for metric in session.feedback.metrics: metric_values[metric.name].append(metric.score)
            for answer in session.questionnaires.values():
                for name in ("confidence", "anxiety", "realism", "usefulness"):
                    value = getattr(answer, name)
                    if value is not None: questionnaires[f"{answer.phase}_{name}"].append(value)
    return users, records, {
        "study_label": settings.pilot_study_label,
        "generated_at": datetime.now(UTC),
        "participants": len(users), "sessions": total_sessions,
        "completed_rehearsals": completed,
        "completion_rate": completed / total_sessions if total_sessions else 0,
        "scenario_completions": dict(scenarios), "difficulty_completions": dict(difficulties),
        "average_skill_scores": {name: sum(values) / len(values) for name, values in metric_values.items()},
        "questionnaire_averages": {name: sum(values) / len(values) for name, values in questionnaires.items()},
        "generation_sources": dict(generation_sources),
        "participant_activity": sorted(records, key=lambda item: item["last_active_at"], reverse=True),
        "privacy": {"contains_names": False, "contains_emails": False, "contains_conversation_text": False, "contains_takeaways": False},
    }


@router.get("/research/dashboard")
async def research_dashboard(user: User = Depends(researcher_user), repository=Depends(get_repository)):
    del user
    _, _, dashboard = await pilot_dataset(repository)
    return dashboard


@router.get("/research/export.csv")
async def research_csv(user: User = Depends(researcher_user), repository=Depends(get_repository)):
    del user
    users = [participant for participant in await repository.list_users() if has_current_study_consent(participant)]
    output = io.StringIO()
    fields = ["participant_id", "session_id", "created_at", "updated_at", "turn_count", "scenario_id", "difficulty", "completion_reason", "pre_confidence", "pre_anxiety", "post_confidence", "post_realism", "post_usefulness"]
    writer = csv.DictWriter(output, fieldnames=fields); writer.writeheader()
    for participant in users:
        for session in await repository.list_sessions(participant.id):
            pre, post = session.questionnaires.get("pre"), session.questionnaires.get("post")
            writer.writerow({
                "participant_id": participant.participant_id, "session_id": session.id,
                "created_at": session.created_at.isoformat(), "updated_at": session.updated_at.isoformat(),
                "turn_count": len(session.turns), "scenario_id": session.roleplay.scenario_id if session.roleplay else "",
                "difficulty": session.roleplay.difficulty_level.value if session.roleplay else "",
                "completion_reason": session.roleplay.completion_reason if session.roleplay else "",
                "pre_confidence": pre.confidence if pre else "", "pre_anxiety": pre.anxiety if pre else "",
                "post_confidence": post.confidence if post else "", "post_realism": post.realism if post else "",
                "post_usefulness": post.usefulness if post else "",
            })
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=affectlab-pilot-export.csv", "Cache-Control": "no-store"})


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
    return [SessionSummary(session_id=s.id, title=s.title, created_at=s.created_at.isoformat(), updated_at=s.updated_at.isoformat(), turn_count=len(s.turns), roleplay=s.roleplay, feedback=s.feedback, takeaway=s.takeaway) for s in await service.list_sessions(user.id)]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    try: session = await service.get_session(session_id, user.id)
    except SessionNotFoundError: raise HTTPException(404, "Session not found") from None
    return SessionResponse(session_id=session.id, title=session.title, turns=session.turns, emotion_state=session.emotion_state, roleplay=session.roleplay, feedback=session.feedback, takeaway=session.takeaway)


@router.patch("/sessions/{session_id}/title", response_model=SessionSummary)
async def rename_session(session_id: UUID, request: SessionTitleRequest, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    try: session = await service.rename_session(session_id, user.id, request.title)
    except SessionNotFoundError: raise HTTPException(404, "Session not found") from None
    return SessionSummary(session_id=session.id, title=session.title, created_at=session.created_at.isoformat(), updated_at=session.updated_at.isoformat(), turn_count=len(session.turns), roleplay=session.roleplay, feedback=session.feedback, takeaway=session.takeaway)


@router.put("/sessions/{session_id}/takeaway", response_model=SessionResponse)
async def save_takeaway(session_id: UUID, request: TakeawayRequest, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    try: session = await service.save_takeaway(session_id, user.id, request.takeaway)
    except SessionNotFoundError: raise HTTPException(404, "Session not found") from None
    return SessionResponse(session_id=session.id, title=session.title, turns=session.turns, emotion_state=session.emotion_state, roleplay=session.roleplay, feedback=session.feedback, takeaway=session.takeaway)


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
async def list_scenarios(user: User = Depends(current_user)): return [*SCENARIOS.values(), *user.custom_scenarios]


@router.post("/roleplay/scenarios", response_model=RolePlayScenario, status_code=201)
async def create_custom_scenario(request: CustomScenarioRequest, user: User = Depends(current_user), repository=Depends(get_repository)):
    allowed = {"clear request", "specific detail", "boundary maintenance", "I-statements", "non-blaming language"}
    skills = list(dict.fromkeys(request.skills))
    if any(skill not in allowed for skill in skills):
        raise HTTPException(422, "Unsupported practice skill")
    conditions = {
        "clear request": "concrete_request", "specific detail": "specific_detail",
        "boundary maintenance": "maintained_boundary", "I-statements": "i_statement",
        "non-blaming language": "no_blame",
    }
    scenario = RolePlayScenario(
        id=f"custom_{uuid4().hex}", title=" ".join(request.title.split()),
        character=" ".join(request.character.split()), situation=request.situation.strip(),
        user_objective=request.user_objective.strip(), opening_line=request.opening_line.strip(),
        expected_skills=skills,
        difficulty_behaviors={Difficulty.BEGINNER:"Supportive and curious", Difficulty.INTERMEDIATE:"Questions details and offers mild resistance", Difficulty.DIFFICULT:"Pushes back firmly while remaining respectful"},
        success_conditions=list(dict.fromkeys(conditions[skill] for skill in skills)), max_turns=8,
    )
    user.custom_scenarios.append(scenario)
    await repository.save_user(user)
    return scenario


@router.delete("/roleplay/scenarios/{scenario_id}", status_code=204)
async def delete_custom_scenario(scenario_id: str, user: User = Depends(current_user), repository=Depends(get_repository)):
    before = len(user.custom_scenarios)
    user.custom_scenarios = [scenario for scenario in user.custom_scenarios if scenario.id != scenario_id]
    if len(user.custom_scenarios) == before: raise HTTPException(404, "Custom scenario not found")
    await repository.save_user(user)


@router.post("/sessions/{session_id}/roleplay", response_model=StartRolePlayResponse)
async def start_roleplay(session_id: UUID, request: StartRolePlayRequest, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    custom = next((scenario for scenario in user.custom_scenarios if scenario.id == request.scenario_id), None)
    if request.scenario_id not in SCENARIOS and not custom: raise HTTPException(404, "Scenario not found")
    try: state, scenario, turn = await service.start_roleplay(session_id, user.id, request.scenario_id, request.difficulty, custom)
    except SessionNotFoundError: raise HTTPException(404, "Session not found") from None
    except KeyError: raise HTTPException(404, "Scenario not found") from None
    return StartRolePlayResponse(state=state, scenario=scenario, opening_turn=turn)


@router.post("/sessions/{session_id}/roleplay/action", response_model=SessionResponse)
async def roleplay_action(session_id: UUID, request: RolePlayActionRequest, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    try: session = await service.set_roleplay_status(session_id, user.id, request.action)
    except SessionNotFoundError: raise HTTPException(404, "Session not found") from None
    except ValueError as exc: raise HTTPException(409, str(exc)) from None
    return SessionResponse(session_id=session.id, title=session.title, turns=session.turns, emotion_state=session.emotion_state, roleplay=session.roleplay, feedback=session.feedback, takeaway=session.takeaway)


@router.post("/sessions/{session_id}/roleplay/rewind", response_model=RewindResponse)
async def rewind_roleplay(session_id: UUID, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    try: removed, session = await service.rewind_roleplay(session_id, user.id)
    except SessionNotFoundError: raise HTTPException(404, "Session not found") from None
    except ValueError as exc: raise HTTPException(409, str(exc)) from None
    return RewindResponse(removed_message=removed, session=SessionResponse(session_id=session.id, title=session.title, turns=session.turns, emotion_state=session.emotion_state, roleplay=session.roleplay, feedback=session.feedback, takeaway=session.takeaway))


@router.get("/sessions/{session_id}/feedback")
async def get_feedback(session_id: UUID, user: User = Depends(current_user), service: ConversationService = Depends(get_conversation_service)):
    session = await service.get_session(session_id, user.id)
    if not session.feedback: raise HTTPException(404, "Feedback not available")
    return session.feedback


@router.put(
    "/sessions/{session_id}/questionnaires/{phase}",
    response_model=StudyQuestionnaireResponse,
)
async def submit_questionnaire(
    session_id: UUID,
    phase: str,
    request: StudyQuestionnaireRequest,
    user: User = Depends(current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        questionnaire = await service.submit_questionnaire(
            session_id, user.id, phase, request.model_dump()
        )
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found") from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    return StudyQuestionnaireResponse(questionnaire=questionnaire)
