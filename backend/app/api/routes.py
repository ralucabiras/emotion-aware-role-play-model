import base64
import binascii
import csv
import hashlib
import hmac
import io
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.container import (
    get_auth_service,
    get_conversation_service,
    get_multimodal_service,
    get_repository,
    get_transcription_service,
)
from app.models.domain import (
    Difficulty,
    FrozenStudyExport,
    RolePlayScenario,
    StudyConsentRecord,
    StudyEligibilityRecord,
    StudyLifecycle,
    StudyWithdrawalRecord,
    User,
    utcnow,
)
from app.repositories.base import RepositoryIndexesNotReadyError
from app.schemas.chat import (
    AudioTranscriptionRequest,
    AudioTranscriptionResponse,
    AuthRequest,
    AuthResponse,
    ChatRequest,
    ChatResponse,
    CreateSessionResponse,
    CustomScenarioRequest,
    DatasetFreezeRequest,
    EmailVerificationRequest,
    MultimodalAffectRequest,
    MultimodalAffectResponse,
    OnboardingRequest,
    ParticipantResearchUpdateRequest,
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
    StudyLifecycleUpdateRequest,
    StudyQuestionnaireRequest,
    StudyQuestionnaireResponse,
    StudyWithdrawalRequest,
    StudyWithdrawalResponse,
    TakeawayRequest,
    UserResponse,
)
from app.services.auth_service import (
    AuthenticationError,
    AuthService,
    EmailNotVerifiedError,
)
from app.services.conversation_service import ConversationService, SessionNotFoundError
from app.services.eligibility import OTHER_CRITERIA, eligibility_version, has_current_eligibility
from app.services.email_service import EmailDeliveryError
from app.services.multimodal_service import (
    MultimodalAffectService,
    MultimodalInferenceUnavailable,
)
from app.services.roleplay_service import SCENARIOS
from app.services.transcription_service import InvalidAudio, TranscriptionService, TranscriptionUnavailable

router, bearer = APIRouter(prefix="/api"), HTTPBearer(auto_error=False)
PROTOCOL_REQUIRED_SCENARIOS = {"workload", "boundary", "relationship"}


def is_researcher(email: str) -> bool:
    allowed = {item.strip().lower() for item in settings.researcher_emails.split(",") if item.strip()}
    return email.strip().lower() in allowed


def has_current_study_consent(user: User) -> bool:
    return bool(
        user.pilot_enrolled_at
        and user.study_consent
        and has_current_eligibility(user)
        and user.study_consent.version == settings.study_consent_version
        and user.study_consent.protocol_version == settings.study_protocol_version
        and not user.study_withdrawal
        and not user.study_excluded_at
    )


def belongs_to_protocol_cohort(user: User) -> bool:
    return bool(
        user.pilot_enrolled_at
        and user.study_consent
        and user.study_consent.protocol_version == settings.study_protocol_version
    )


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie("refresh_token", token, httponly=True, samesite="lax", secure=settings.production, path="/api/auth", max_age=settings.refresh_token_days * 86400)


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


@router.get("/health/live")
async def health_live():
    return {"status": "alive"}


@router.get("/health/ready")
async def health_ready(repository=Depends(get_repository)):
    checks = {"configuration": "ok", "persistence": "pending", "indexes": "pending"}
    try:
        settings.__class__.model_validate(settings.model_dump())
    except Exception:
        checks["configuration"] = "failed"
        return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})
    try:
        await repository.check_readiness()
    except RepositoryIndexesNotReadyError:
        checks["persistence"] = "ok"
        checks["indexes"] = "failed"
        return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})
    except Exception:
        checks["persistence"] = "failed"
        checks["indexes"] = "unknown"
        return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})
    checks["persistence"] = "ok"
    checks["indexes"] = "ok"
    multimodal = get_multimodal_service()
    transcription = get_transcription_service()
    return {
        "status": "ready",
        "checks": checks,
        "optional_services": {
            "multimodal_model": {"available": multimodal.available, "status": multimodal.status},
            "transcription": {"available": transcription.available},
        },
    }


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
        eligibility_version=user.study_eligibility.version if user.study_eligibility else None,
        eligibility_confirmed_at=user.study_eligibility.confirmed_at.isoformat() if user.study_eligibility else None,
        study_withdrawn=bool(user.study_withdrawal),
        study_withdrawn_at=(user.study_withdrawal.withdrawn_at.isoformat() if user.study_withdrawal else None),
        participant_id=user.participant_id,
    )


@router.post("/auth/register", response_model=RegistrationResponse, status_code=202)
async def register(request: AuthRequest, response: Response, auth: AuthService = Depends(get_auth_service)):
    profile = request.model_dump(
        include={"first_name", "last_name", "preferred_name", "country", "timezone"}
    )
    try:
        try:
            await auth.register(str(request.email), request.password, request.consent, profile)
        except ValueError as exc:
            if str(exc) != "duplicate email":
                raise HTTPException(400, str(exc)) from None
            # Handle the unique-insert conflict too; never overwrite existing credentials.
            await auth.resend_verification(str(request.email))
    except EmailDeliveryError:
        pass
    return RegistrationResponse(
        message="Request accepted. If this email is eligible for confirmation, check your inbox. You can also sign in or request a password reset.",
        email=str(request.email).strip().lower(),
    )


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
    records = await repository.list_study_records(user.id)
    return {
        "schema_version": "affectlab-research-export-v2",
        "protocol_version": settings.study_protocol_version,
        "participant_id": str(user.participant_id),
        "account_privacy_acceptance": {"version": user.consent_version, "accepted_at": user.consented_at},
        "study_consent": user.study_consent.model_dump(mode="json") if user.study_consent else None,
        "study_eligibility": user.study_eligibility.model_dump(mode="json") if user.study_eligibility else None,
        "study_withdrawal": user.study_withdrawal.model_dump(mode="json") if user.study_withdrawal else None,
        "practice_goals": [goal.value for goal in user.practice_goals],
        "contains_conversation_text": False,
        "records": [
            {
                "session_id": str(record.session_id),
                "protocol_version": record.protocol_version,
                "session_created_at": record.session_created_at,
                "last_activity_at": record.last_activity_at,
                "retention_expires_at": record.retention_expires_at,
                "turn_count": record.turn_count,
                "scenario_id": record.scenario_id,
                "difficulty": record.difficulty,
                "completion_reason": record.completion_reason,
                "feedback_metrics": [metric.model_dump(mode="json") for metric in record.feedback_metrics],
                "feedback_generation_source": record.feedback_generation_source,
                "questionnaires": {
                    phase: answer.model_dump(mode="json")
                    for phase, answer in record.questionnaires.items()
                },
                "events": [event.model_dump(mode="json") for event in record.events],
            }
            for record in records
        ],
    }


@router.get("/research/study-information", response_model=StudyInformationResponse)
async def study_information(user: User = Depends(current_user)):
    return StudyInformationResponse(
        eligibility_version=eligibility_version(),
        minimum_participant_age=settings.minimum_participant_age,
        geographic_scope=settings.geographic_scope,
        supported_language=settings.supported_language,
        other_eligibility_criteria=OTHER_CRITERIA,
        version=settings.study_consent_version,
        protocol_version=settings.study_protocol_version,
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
            f"Eligibility is limited to people aged {settings.minimum_participant_age} or over, located in {settings.geographic_scope}, using {settings.supported_language}.",
            "Discussing difficult situations may feel uncomfortable; you may pause or stop at any time.",
            "Emotion estimates and generated replies can be inaccurate, biased, repetitive, or inappropriate.",
            "AffectLab is not therapy, diagnosis, medical advice, or an emergency service.",
            settings.emergency_limitations,
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
    lifecycle = await repository.get_study_lifecycle(settings.study_protocol_version)
    if lifecycle and (lifecycle.dataset_frozen_at or lifecycle.freeze_token):
        raise HTTPException(409, "The study dataset is frozen and enrollment is closed")
    today = datetime.now(UTC).date()
    if lifecycle and lifecycle.start_date and today < lifecycle.start_date:
        raise HTTPException(409, "Study enrollment has not opened")
    if lifecycle and lifecycle.end_date and today > lifecycle.end_date:
        raise HTTPException(409, "Study enrollment has closed")
    if not hmac.compare_digest(request.access_code, settings.pilot_access_code):
        raise HTTPException(400, "The pilot access code is not valid")
    if user.study_withdrawal:
        raise HTTPException(409, "This account has withdrawn from the pilot study")
    if user.study_excluded_at:
        raise HTTPException(409, "This account is excluded from the pilot study")
    if request.consent_version != settings.study_consent_version:
        raise HTTPException(409, "The participant information has changed. Review the current version before consenting.")
    if not all((request.information_sheet_read, request.research_participation_accepted, request.data_processing_accepted)):
        raise HTTPException(400, "All study consent confirmations are required")
    if request.eligibility_version != eligibility_version():
        raise HTTPException(409, "Eligibility criteria have changed. Review and confirm the current criteria.")
    if not all((request.age_confirmed, request.geography_confirmed, request.english_confirmed, request.other_criteria_confirmed)):
        raise HTTPException(400, "All eligibility confirmations are required")
    user.study_eligibility = StudyEligibilityRecord(version=eligibility_version(), protocol_version=settings.study_protocol_version)
    if not user.pilot_enrolled_at:
        user.pilot_enrolled_at = utcnow()
    user.study_consent = StudyConsentRecord(
        version=settings.study_consent_version,
        protocol_version=settings.study_protocol_version,
        information_sheet_read=request.information_sheet_read,
        research_participation_accepted=request.research_participation_accepted,
        data_processing_accepted=request.data_processing_accepted,
    )
    await repository.save_user(user)
    return user_response(user)


@router.post("/research/withdraw", response_model=StudyWithdrawalResponse)
async def withdraw_from_study(
    request: StudyWithdrawalRequest,
    user: User = Depends(current_user),
    repository=Depends(get_repository),
):
    if not request.confirm_withdrawal:
        raise HTTPException(400, "Explicit withdrawal confirmation is required")
    if not user.study_consent or not user.pilot_enrolled_at:
        raise HTTPException(409, "This account is not enrolled in the pilot study")
    if user.study_withdrawal:
        raise HTTPException(409, "This account has already withdrawn from the pilot study")

    records = await repository.list_study_records(user.id)
    questionnaires_deleted = sum(len(record.questionnaires) for record in records)
    research_events_deleted = sum(len(record.events) for record in records)
    for session in await repository.list_sessions(user.id):
        session.questionnaires = {}
        session.research_events = []
        await repository.save_session(session)
    await repository.delete_study_records(user.id)

    user.study_withdrawal = StudyWithdrawalRecord(consent_version=user.study_consent.version)
    await repository.save_user(user)
    return StudyWithdrawalResponse(
        user=user_response(user),
        questionnaires_deleted=questionnaires_deleted,
        research_events_deleted=research_events_deleted,
        message="You have withdrawn from the pilot study. Your AffectLab account remains available.",
        anonymized_analysis_notice=(
            "Your account is excluded from future research exports. Study questionnaires and research-event telemetry still held by AffectLab were deleted. Data already irreversibly anonymised or included in completed aggregate analysis may no longer be identifiable and therefore may not be removable."
        ),
    )


async def pilot_dataset(repository):
    cohort = [user for user in await repository.list_users() if belongs_to_protocol_cohort(user)]
    users = [user for user in cohort if has_current_study_consent(user)]
    all_records = await repository.list_study_records()
    metric_values: dict[str, list[float]] = defaultdict(list)
    scenarios: dict[str, int] = defaultdict(int)
    difficulties: dict[str, int] = defaultdict(int)
    questionnaires: dict[str, list[float]] = defaultdict(list)
    generation_sources: dict[str, int] = defaultdict(int)
    total_sessions = completed = protocol_completers = 0
    activity_records = []
    for user in cohort:
        study_records = [record for record in all_records if record.user_id == user.id]
        eligible = has_current_study_consent(user)
        if eligible: total_sessions += len(study_records)
        user_completed = sum(bool(record.completion_reason) for record in study_records)
        qualifying_scenarios = {
            record.scenario_id
            for record in study_records
            if record.scenario_id in PROTOCOL_REQUIRED_SCENARIOS
            and record.difficulty == Difficulty.INTERMEDIATE
            and record.completion_reason
            and "post" in record.questionnaires
        }
        protocol_complete = qualifying_scenarios == PROTOCOL_REQUIRED_SCENARIOS
        if eligible:
            protocol_completers += int(protocol_complete)
            completed += user_completed
        last_active = max((record.last_activity_at for record in study_records), default=user.pilot_enrolled_at)
        activity_records.append({
            "participant_id": str(user.participant_id),
            "enrolled_at": user.pilot_enrolled_at,
            "last_active_at": last_active,
            "sessions": len(study_records),
            "completed_rehearsals": user_completed,
            "protocol_complete": protocol_complete,
            "completion_status": "withdrawn" if user.study_withdrawal else "excluded" if user.study_excluded_at else "complete" if protocol_complete else "in_progress",
            "excluded": bool(user.study_excluded_at),
            "withdrawn": bool(user.study_withdrawal),
            "exclusion_reason": user.study_exclusion_reason,
            "data_quality_notes": user.study_data_quality_notes,
            "pre_questionnaires": sum("pre" in record.questionnaires for record in study_records),
            "post_questionnaires": sum("post" in record.questionnaires for record in study_records),
        })
        if not eligible:
            continue
        for record in study_records:
            if record.scenario_id and record.completion_reason:
                scenarios[record.scenario_id] += 1
                if record.difficulty: difficulties[record.difficulty.value] += 1
            if record.feedback_generation_source:
                generation_sources[record.feedback_generation_source] += 1
                for metric in record.feedback_metrics: metric_values[metric.name].append(metric.score)
            for answer in record.questionnaires.values():
                for name in ("confidence", "anxiety", "realism", "usefulness"):
                    value = getattr(answer, name)
                    if value is not None: questionnaires[f"{answer.phase}_{name}"].append(value)
    lifecycle = await repository.get_study_lifecycle(settings.study_protocol_version)
    frozen_export = (
        await repository.get_frozen_export(lifecycle.frozen_export_id)
        if lifecycle and lifecycle.frozen_export_id else None
    )
    return users, activity_records, {
        "study_label": settings.pilot_study_label,
        "protocol_version": settings.study_protocol_version,
        "generated_at": datetime.now(UTC),
        "participants": len(users), "sessions": total_sessions,
        "participant_target": settings.study_participant_target,
        "completed_rehearsals": completed,
        "protocol_completers": protocol_completers,
        "completer_target": settings.study_completer_target,
        "protocol_completion_rate": protocol_completers / len(users) if users else 0,
        "completion_rate": completed / total_sessions if total_sessions else 0,
        "scenario_completions": dict(scenarios), "difficulty_completions": dict(difficulties),
        "average_skill_scores": {name: sum(values) / len(values) for name, values in metric_values.items()},
        "questionnaire_averages": {name: sum(values) / len(values) for name, values in questionnaires.items()},
        "generation_sources": dict(generation_sources),
        "participant_activity": sorted(activity_records, key=lambda item: item["last_active_at"], reverse=True),
        "lifecycle": lifecycle.model_dump(mode="json") if lifecycle else {
            "protocol_version": settings.study_protocol_version,
            "start_date": None, "end_date": None, "dataset_frozen_at": None,
            "frozen_export_id": None,
        },
        "frozen_export": ({
            "export_id": str(frozen_export.id),
            "schema_version": frozen_export.schema_version,
            "created_at": frozen_export.created_at,
            "record_count": frozen_export.record_count,
            "participant_count": frozen_export.participant_count,
            "sha256": frozen_export.sha256,
        } if frozen_export else None),
        "privacy": {"contains_names": False, "contains_emails": False, "contains_conversation_text": False, "contains_takeaways": False},
    }


@router.get("/research/dashboard")
async def research_dashboard(user: User = Depends(researcher_user), repository=Depends(get_repository)):
    del user
    _, _, dashboard = await pilot_dataset(repository)
    return dashboard


@router.put("/research/lifecycle")
async def update_research_lifecycle(
    request: StudyLifecycleUpdateRequest,
    user: User = Depends(researcher_user),
    repository=Depends(get_repository),
):
    del user
    if request.end_date < request.start_date:
        raise HTTPException(400, "Study end date must not precede the start date")
    current = await repository.get_study_lifecycle(settings.study_protocol_version)
    if current and (current.dataset_frozen_at or current.freeze_token):
        raise HTTPException(409, "The study lifecycle cannot be edited during or after dataset freeze")
    lifecycle = current or StudyLifecycle(protocol_version=settings.study_protocol_version)
    lifecycle.start_date, lifecycle.end_date, lifecycle.updated_at = (
        request.start_date, request.end_date, utcnow()
    )
    return await repository.save_study_lifecycle(lifecycle)


@router.patch("/research/participants/{participant_id}")
async def update_participant_research_status(
    participant_id: UUID,
    request: ParticipantResearchUpdateRequest,
    user: User = Depends(researcher_user),
    repository=Depends(get_repository),
):
    del user
    lifecycle = await repository.get_study_lifecycle(settings.study_protocol_version)
    if lifecycle and (lifecycle.dataset_frozen_at or lifecycle.freeze_token):
        raise HTTPException(409, "Participant research data cannot be edited during or after dataset freeze")
    participant = next(
        (item for item in await repository.list_users() if item.participant_id == participant_id),
        None,
    )
    if not participant or not belongs_to_protocol_cohort(participant):
        raise HTTPException(404, "Study participant not found")
    if participant.study_withdrawal:
        raise HTTPException(409, "A withdrawn participant record cannot be edited")
    if request.excluded and not request.exclusion_reason.strip():
        raise HTTPException(400, "An exclusion reason is required")
    participant.study_excluded_at = utcnow() if request.excluded else None
    participant.study_exclusion_reason = request.exclusion_reason.strip() if request.excluded else ""
    participant.study_data_quality_notes = request.data_quality_notes.strip()
    await repository.save_user(participant)
    return {"participant_id": participant.participant_id, "excluded": bool(participant.study_excluded_at)}


async def build_research_csv(repository, deidentified: bool = False) -> tuple[str, int, int]:
    users = [participant for participant in await repository.list_users() if has_current_study_consent(participant)]
    users.sort(key=lambda participant: (participant.pilot_enrolled_at, str(participant.participant_id)))
    output = io.StringIO()
    fields = ["protocol_version", "participant_id", "session_id", "created_at", "updated_at", "turn_count", "scenario_id", "difficulty", "completion_reason", "pre_confidence", "pre_anxiety", "post_confidence", "post_realism", "post_usefulness"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    count = 0
    for participant_index, participant in enumerate(users, 1):
        records = await repository.list_study_records(participant.id)
        records.sort(key=lambda record: (record.session_created_at, str(record.session_id)))
        for session_index, record in enumerate(records, 1):
            pre, post = record.questionnaires.get("pre"), record.questionnaires.get("post")
            writer.writerow({
                "protocol_version": record.protocol_version,
                "participant_id": f"P{participant_index:04d}" if deidentified else participant.participant_id,
                "session_id": f"P{participant_index:04d}-S{session_index:03d}" if deidentified else record.session_id,
                "created_at": record.session_created_at.isoformat(), "updated_at": record.last_activity_at.isoformat(),
                "turn_count": record.turn_count, "scenario_id": record.scenario_id or "",
                "difficulty": record.difficulty.value if record.difficulty else "",
                "completion_reason": record.completion_reason or "",
                "pre_confidence": pre.confidence if pre else "", "pre_anxiety": pre.anxiety if pre else "",
                "post_confidence": post.confidence if post else "", "post_realism": post.realism if post else "",
                "post_usefulness": post.usefulness if post else "",
            })
            count += 1
    return output.getvalue(), count, len(users)


@router.post("/research/freeze")
async def freeze_research_dataset(
    request: DatasetFreezeRequest,
    user: User = Depends(researcher_user),
    repository=Depends(get_repository),
):
    if not request.confirm_freeze:
        raise HTTPException(400, "Explicit dataset-freeze confirmation is required")
    lifecycle = await repository.get_study_lifecycle(settings.study_protocol_version)
    if not lifecycle or not lifecycle.start_date or not lifecycle.end_date:
        raise HTTPException(409, "Set study start and end dates before freezing the dataset")
    if lifecycle.end_date > datetime.now(UTC).date():
        raise HTTPException(409, "The study end date must be reached before dataset freeze")
    if lifecycle.dataset_frozen_at:
        raise HTTPException(409, "The study dataset is already frozen")
    freeze_token = uuid4()
    lifecycle = await repository.begin_dataset_freeze(settings.study_protocol_version, freeze_token)
    if not lifecycle:
        raise HTTPException(409, "The study dataset is already frozen or a freeze is in progress")
    try:
        content, record_count, participant_count = await build_research_csv(repository, True)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        frozen = FrozenStudyExport(
            protocol_version=settings.study_protocol_version,
            record_count=record_count,
            participant_count=participant_count,
            sha256=digest,
            csv_content=content,
        )
        await repository.complete_dataset_freeze(frozen, freeze_token)
    except Exception:
        await repository.abort_dataset_freeze(settings.study_protocol_version, freeze_token)
        raise
    return {
        "export_id": frozen.id, "protocol_version": frozen.protocol_version,
        "schema_version": frozen.schema_version, "created_at": frozen.created_at,
        "record_count": record_count, "participant_count": participant_count,
        "sha256": digest,
    }


@router.get("/research/export.csv")
async def research_csv(user: User = Depends(researcher_user), repository=Depends(get_repository)):
    del user
    lifecycle = await repository.get_study_lifecycle(settings.study_protocol_version)
    frozen = await repository.get_frozen_export(lifecycle.frozen_export_id) if lifecycle and lifecycle.frozen_export_id else None
    if frozen:
        content, filename = frozen.csv_content, f"affectlab-frozen-{frozen.id}.csv"
        checksum = frozen.sha256
    else:
        content, _, _ = await build_research_csv(repository)
        filename, checksum = "affectlab-pilot-live-export.csv", hashlib.sha256(content.encode("utf-8")).hexdigest()
    return Response(content=content, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}", "Cache-Control": "no-store", "X-Content-SHA256": checksum})


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
