import base64
import io
import wave

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.container import (
    auth_service,
    get_multimodal_service,
    get_repository,
    get_transcription_service,
    repository,
)
from app.main import app
from app.repositories.base import RepositoryIndexesNotReadyError
from app.repositories.mongo import ConcurrentSessionUpdateError
from app.services.eligibility import eligibility_version
from app.services.multimodal_service import MultimodalAffectService
from app.services.transcription_service import TranscriptionResult


class CapturingEmailService:
    def __init__(self) -> None:
        self.tokens: dict[str, str] = {}
        self.reset_tokens: dict[str, str] = {}

    async def send_verification(self, recipient: str, preferred_name: str, token: str) -> None:
        self.tokens[recipient] = token

    async def send_password_reset(self, recipient: str, preferred_name: str, token: str) -> None:
        self.reset_tokens[recipient] = token


capturing_email = CapturingEmailService()
auth_service.email_service = capturing_email


def test_liveness_and_readiness_health_contracts() -> None:
    with TestClient(app) as client:
        live = client.get("/api/health/live")
        ready = client.get("/api/health/ready")

        assert live.status_code == 200
        assert live.json() == {"status": "alive"}
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"
        assert ready.json()["checks"] == {
            "configuration": "ok",
            "persistence": "ok",
            "indexes": "ok",
        }
        assert set(ready.json()["optional_services"]) == {
            "multimodal_model",
            "transcription",
        }


def test_readiness_returns_503_when_persistence_is_unavailable() -> None:
    class UnavailableRepository:
        async def check_readiness(self) -> None:
            raise RuntimeError("sensitive database connection detail")

    app.dependency_overrides[get_repository] = lambda: UnavailableRepository()
    try:
        with TestClient(app) as client:
            response = client.get("/api/health/ready")
    finally:
        app.dependency_overrides.pop(get_repository, None)

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {
            "configuration": "ok",
            "persistence": "failed",
            "indexes": "unknown",
        },
    }
    assert "sensitive" not in response.text


def test_readiness_distinguishes_missing_indexes_from_database_failure() -> None:
    class RepositoryWithMissingIndexes:
        async def check_readiness(self) -> None:
            raise RepositoryIndexesNotReadyError("missing private_index_name")

    app.dependency_overrides[get_repository] = lambda: RepositoryWithMissingIndexes()
    try:
        with TestClient(app) as client:
            response = client.get("/api/health/ready")
    finally:
        app.dependency_overrides.pop(get_repository, None)

    assert response.status_code == 503
    assert response.json()["checks"] == {
        "configuration": "ok",
        "persistence": "ok",
        "indexes": "failed",
    }
    assert "private_index_name" not in response.text


def auth(client: TestClient, email: str = "user@example.com") -> dict[str, str]:
    result = client.post("/api/auth/register", json={"email": email, "password": "long-test-password", "consent": True})
    assert result.status_code == 202
    verification = client.post(
        "/api/auth/verify-email", json={"token": capturing_email.tokens[email]}
    )
    assert verification.status_code == 200
    login = client.post(
        "/api/auth/login", json={"email": email, "password": "long-test-password"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_auth_session_chat_and_feedback() -> None:
    with TestClient(app) as client:
        headers = auth(client)
        assert client.get("/api/auth/me", headers=headers).status_code == 200
        session_id = client.post("/api/sessions", headers=headers).json()["session_id"]
        renamed = client.patch(f"/api/sessions/{session_id}/title", headers=headers, json={"title": "  Manager preparation  "})
        assert renamed.status_code == 200
        assert renamed.json()["title"] == "Manager preparation"
        response = client.post("/api/chat", headers=headers, json={"session_id": session_id, "message": "I'm scared they will think I'm incompetent"})
        assert response.status_code == 200
        assert response.json()["decision"]["strategy"] == "validate_then_reframe"
        start = client.post(f"/api/sessions/{session_id}/roleplay", headers=headers, json={"scenario_id": "workload", "difficulty": "beginner"})
        assert start.status_code == 200
        roleplay_session = client.get(f"/api/sessions/{session_id}", headers=headers).json()
        assert len(roleplay_session["turns"]) == 1
        assert roleplay_session["turns"][0]["content"] == start.json()["opening_turn"]["content"]
        reply = client.post("/api/chat", headers=headers, json={"session_id": session_id, "message": "I need you to prioritise the deadline because it is this week"}).json()
        assert reply["roleplay"]["status"] == "completed"
        assert reply["feedback"]["metrics"]
        history = client.get("/api/sessions", headers=headers).json()
        assert history[0]["title"] == "Workload conversation"
        assert history[0]["feedback"]["metrics"]


def test_concurrent_session_update_returns_reloadable_conflict(monkeypatch) -> None:
    with TestClient(app) as client:
        headers = auth(client, "concurrent-edit@example.com")
        session_id = client.post("/api/sessions", headers=headers).json()["session_id"]

        async def reject_stale_save(session):
            del session
            raise ConcurrentSessionUpdateError("Session was updated by another request")

        monkeypatch.setattr(repository, "save_session", reject_stale_save)
        response = client.patch(
            f"/api/sessions/{session_id}/title",
            headers=headers,
            json={"title": "A stale edit"},
        )

        assert response.status_code == 409
        assert response.json() == {
            "detail": (
                "This session changed in another browser or tab. "
                "Reload the session, review the latest changes, and try again."
            ),
            "code": "session_update_conflict",
        }


def test_ownership_and_crisis_precedence() -> None:
    with TestClient(app) as client:
        first, second = auth(client, "one@example.com"), auth(client, "two@example.com")
        session_id = client.post("/api/sessions", headers=first).json()["session_id"]
        assert client.get(f"/api/sessions/{session_id}", headers=second).status_code == 404
        body = client.post("/api/chat", headers=first, json={"session_id": session_id, "message": "I want to kill myself"}).json()
        assert body["decision"]["strategy"] == "safety_escalation"


def test_refresh_rotation_logout_and_delete() -> None:
    with TestClient(app) as client:
        headers = auth(client, "refresh@example.com")
        assert client.post("/api/auth/refresh").status_code == 200
        assert client.post("/api/auth/logout", headers=headers).status_code == 204
        headers = {"Authorization": f"Bearer {client.post('/api/auth/login', json={'email':'refresh@example.com','password':'long-test-password'}).json()['access_token']}"}
        assert client.delete("/api/auth/me", headers=headers).status_code == 204


def test_profile_update_and_password_change() -> None:
    with TestClient(app) as client:
        headers = auth(client, "settings@example.com")
        profile = client.patch(
            "/api/auth/me",
            headers=headers,
            json={"first_name": "Ralu", "last_name": "B", "preferred_name": "Ral", "country": "Romania", "timezone": "Europe/Bucharest"},
        )
        assert profile.status_code == 200
        assert profile.json()["preferred_name"] == "Ral"
        wrong = client.post(
            "/api/auth/change-password",
            headers=headers,
            json={"current_password": "incorrect-password", "new_password": "new-long-password"},
        )
        assert wrong.status_code == 400
        changed = client.post(
            "/api/auth/change-password",
            headers=headers,
            json={"current_password": "long-test-password", "new_password": "new-long-password"},
        )
        assert changed.status_code == 204
        assert client.post("/api/auth/login", json={"email": "settings@example.com", "password": "long-test-password"}).status_code == 401
        assert client.post("/api/auth/login", json={"email": "settings@example.com", "password": "new-long-password"}).status_code == 200


def test_guided_onboarding_persists_one_to_three_practice_goals() -> None:
    with TestClient(app) as client:
        headers = auth(client, "onboarding@example.com")
        initial = client.get("/api/auth/me", headers=headers).json()
        assert initial["onboarding_completed"] is False
        assert initial["practice_goals"] == []

        completed = client.put(
            "/api/auth/onboarding",
            headers=headers,
            json={"practice_goals": ["assertiveness", "clear_requests"]},
        )
        assert completed.status_code == 200
        assert completed.json()["onboarding_completed"] is True
        assert completed.json()["practice_goals"] == ["assertiveness", "clear_requests"]
        assert client.get("/api/auth/me", headers=headers).json()["practice_goals"] == ["assertiveness", "clear_requests"]

        assert client.put("/api/auth/onboarding", headers=headers, json={"practice_goals": []}).status_code == 422
        assert client.put(
            "/api/auth/onboarding",
            headers=headers,
            json={"practice_goals": ["assertiveness", "clear_requests", "reduce_apologising", "prepare_conversation"]},
        ).status_code == 422


def test_custom_scenario_and_rewind_are_owned_and_preserve_history() -> None:
    with TestClient(app) as client:
        headers = auth(client, "custom-scenario@example.com")
        created = client.post(
            "/api/roleplay/scenarios",
            headers=headers,
            json={
                "title": "Requesting flexible hours",
                "character": "team lead",
                "situation": "A recurring appointment conflicts with the current schedule.",
                "user_objective": "Ask for a predictable change to the weekly schedule.",
                "opening_line": "You wanted to discuss your schedule. What do you need?",
                "skills": ["clear request", "specific detail", "non-blaming language"],
            },
        )
        assert created.status_code == 201
        scenario = created.json()
        assert scenario["id"].startswith("custom_")
        assert any(item["id"] == scenario["id"] for item in client.get("/api/roleplay/scenarios", headers=headers).json())

        session_id = client.post("/api/sessions", headers=headers).json()["session_id"]
        started = client.post(
            f"/api/sessions/{session_id}/roleplay",
            headers=headers,
            json={"scenario_id": scenario["id"], "difficulty": "intermediate"},
        )
        assert started.status_code == 200
        assert started.json()["state"]["scenario"]["title"] == "Requesting flexible hours"
        reply = client.post(
            "/api/chat", headers=headers,
            json={"session_id": session_id, "message": "I am not sure how to put this yet."},
        )
        assert reply.status_code == 200
        rewound = client.post(f"/api/sessions/{session_id}/roleplay/rewind", headers=headers)
        assert rewound.status_code == 200
        assert rewound.json()["removed_message"] == "I am not sure how to put this yet."
        assert rewound.json()["session"]["roleplay"]["turn"] == 0
        assert len(rewound.json()["session"]["turns"]) == 1

        assert client.delete(f"/api/roleplay/scenarios/{scenario['id']}", headers=headers).status_code == 204
        restored = client.get(f"/api/sessions/{session_id}", headers=headers).json()
        assert restored["roleplay"]["scenario"]["title"] == "Requesting flexible hours"


def test_feedback_compares_previous_matching_attempt_and_saves_takeaway() -> None:
    with TestClient(app) as client:
        headers = auth(client, "comparison@example.com")

        def complete_workload(message: str) -> tuple[str, dict]:
            session_id = client.post("/api/sessions", headers=headers).json()["session_id"]
            assert client.post(
                f"/api/sessions/{session_id}/roleplay", headers=headers,
                json={"scenario_id": "workload", "difficulty": "beginner"},
            ).status_code == 200
            result = client.post(
                "/api/chat", headers=headers,
                json={"session_id": session_id, "message": message},
            ).json()
            return session_id, result["feedback"]

        first_id, first_feedback = complete_workload(
            "I need you to prioritise this because the deadline is Friday."
        )
        assert first_feedback["comparisons"] == []
        second_id, second_feedback = complete_workload(
            "I would like us to prioritise this because the deadline is this week."
        )
        assert second_feedback["compared_with_session_id"] == first_id
        assert second_feedback["comparisons"]
        assert {item["name"] for item in second_feedback["comparisons"]} == {
            "clear request", "specific evidence", "collaborative tone"
        }

        saved = client.put(
            f"/api/sessions/{second_id}/takeaway", headers=headers,
            json={"takeaway": "  Lead with the request, then give the deadline.  "},
        )
        assert saved.status_code == 200
        assert saved.json()["takeaway"] == "Lead with the request, then give the deadline."
        history = client.get("/api/sessions", headers=headers).json()
        assert next(item for item in history if item["session_id"] == second_id)["takeaway"] == "Lead with the request, then give the deadline."


def test_pilot_enrollment_and_researcher_dashboard_exclude_identity_and_text() -> None:
    previous_emails, previous_code = settings.researcher_emails, settings.pilot_access_code
    settings.researcher_emails = "researcher@example.com"
    settings.pilot_access_code = "pilot-code-2026"
    try:
        with TestClient(app) as client:
            participant_headers = auth(client, "pilot-participant@example.com")
            information = client.get("/api/research/study-information", headers=participant_headers)
            assert information.status_code == 200
            version = information.json()["version"]
            assert information.json()["data_collected"]
            assert information.json()["withdrawal"]
            consent = {
                "consent_version": version,
                "information_sheet_read": True,
                "research_participation_accepted": True,
                "data_processing_accepted": True,
                "eligibility_version": eligibility_version(),
                "age_confirmed": True,
                "geography_confirmed": True,
                "english_confirmed": True,
                "other_criteria_confirmed": True,
            }
            invalid = client.post("/api/research/enroll", headers=participant_headers, json={"access_code": "wrong", **consent})
            assert invalid.status_code == 400
            missing_consent = client.post("/api/research/enroll", headers=participant_headers, json={"access_code": "pilot-code-2026", **consent, "research_participation_accepted": False})
            assert missing_consent.status_code == 400
            stale = client.post("/api/research/enroll", headers=participant_headers, json={"access_code": "pilot-code-2026", **consent, "consent_version": "old-version"})
            assert stale.status_code == 409
            for field in ("age_confirmed", "geography_confirmed", "english_confirmed", "other_criteria_confirmed"):
                for value in (False, None, "true"):
                    rejected = client.post("/api/research/enroll", headers=participant_headers, json={"access_code": "pilot-code-2026", **consent, field: value})
                    assert rejected.status_code in (400, 422)
                missing = {key: value for key, value in consent.items() if key != field}
                assert client.post("/api/research/enroll", headers=participant_headers, json={"access_code": "pilot-code-2026", **missing}).status_code == 400
            assert client.get("/api/auth/me", headers=participant_headers).json()["eligibility_confirmed_at"] is None
            assert client.post("/api/research/enroll", headers=participant_headers, json={"access_code": "pilot-code-2026", **consent, "eligibility_version": "stale"}).status_code == 409
            enrolled = client.post("/api/research/enroll", headers=participant_headers, json={"access_code": "pilot-code-2026", **consent})
            assert enrolled.status_code == 200
            assert enrolled.json()["pilot_enrolled"] is True
            assert enrolled.json()["study_consent_version"] == version
            assert enrolled.json()["study_consented_at"]
            assert enrolled.json()["eligibility_version"] == information.json()["eligibility_version"]
            assert enrolled.json()["eligibility_confirmed_at"]
            previous_scope = settings.geographic_scope
            try:
                settings.geographic_scope = "Changed scope"
                assert client.get("/api/auth/me", headers=participant_headers).json()["pilot_enrolled"] is False
            finally:
                settings.geographic_scope = previous_scope
            participant_id = enrolled.json()["participant_id"]
            session_id = client.post("/api/sessions", headers=participant_headers).json()["session_id"]
            client.post("/api/chat", headers=participant_headers, json={"session_id": session_id, "message": "private pilot conversation text"})
            assert client.get("/api/research/dashboard", headers=participant_headers).status_code == 403

            researcher_headers = auth(client, "researcher@example.com")
            researcher_me = client.get("/api/auth/me", headers=researcher_headers).json()
            assert researcher_me["researcher"] is True
            dashboard = client.get("/api/research/dashboard", headers=researcher_headers)
            assert dashboard.status_code == 200
            assert dashboard.json()["participants"] == 1
            assert dashboard.json()["participant_activity"][0]["participant_id"] == participant_id
            serialized = dashboard.text
            assert "pilot-participant@example.com" not in serialized
            assert "private pilot conversation text" not in serialized
            export = client.get("/api/research/export.csv", headers=researcher_headers)
            assert export.status_code == 200
            assert "text/csv" in export.headers["content-type"]
            assert participant_id in export.text
            assert "pilot-participant@example.com" not in export.text
            assert "private pilot conversation text" not in export.text
            personal_export = client.get("/api/auth/research-export", headers=participant_headers).json()
            assert personal_export["study_consent"]["version"] == version
            assert personal_export["study_consent"]["accepted_at"]
            assert set(personal_export["study_eligibility"]) == {"version", "protocol_version", "confirmed_at"}
            assert personal_export["study_eligibility"]["confirmed_at"].replace("Z", "+00:00") == enrolled.json()["eligibility_confirmed_at"]

            client.put(
                f"/api/sessions/{session_id}/questionnaires/pre",
                headers=participant_headers,
                json={"confidence": 4, "anxiety": 6},
            )
            unconfirmed = client.post(
                "/api/research/withdraw",
                headers=participant_headers,
                json={"confirm_withdrawal": False},
            )
            assert unconfirmed.status_code == 400
            withdrawn = client.post(
                "/api/research/withdraw",
                headers=participant_headers,
                json={"confirm_withdrawal": True},
            )
            assert withdrawn.status_code == 200
            withdrawal = withdrawn.json()
            assert withdrawal["user"]["study_withdrawn"] is True
            assert withdrawal["user"]["pilot_enrolled"] is False
            assert withdrawal["user"]["study_withdrawn_at"]
            assert withdrawal["questionnaires_deleted"] == 1
            assert withdrawal["research_events_deleted"] > 0
            assert "irreversibly anonymised" in withdrawal["anonymized_analysis_notice"]

            retained_session = client.get(
                f"/api/sessions/{session_id}", headers=participant_headers
            )
            assert retained_session.status_code == 200
            assert "private pilot conversation text" in retained_session.text
            withdrawn_export = client.get(
                "/api/auth/research-export", headers=participant_headers
            ).json()
            assert withdrawn_export["study_withdrawal"]["withdrawn_at"]
            assert withdrawn_export["records"] == []
            assert client.get(
                "/api/research/dashboard", headers=researcher_headers
            ).json()["participants"] == 0
            assert participant_id not in client.get(
                "/api/research/export.csv", headers=researcher_headers
            ).text
            assert client.post(
                "/api/research/enroll",
                headers=participant_headers,
                json={"access_code": "pilot-code-2026", **consent},
            ).status_code == 409
    finally:
        settings.researcher_emails, settings.pilot_access_code = previous_emails, previous_code


def test_research_lifecycle_review_and_immutable_frozen_export() -> None:
    previous = (
        settings.researcher_emails,
        settings.pilot_access_code,
        settings.study_protocol_version,
    )
    settings.researcher_emails = "freeze-researcher@example.com"
    settings.pilot_access_code = "freeze-code"
    settings.study_protocol_version = "freeze-test-v1"
    try:
        with TestClient(app) as client:
            participant_headers = auth(client, "freeze-participant@example.com")
            information = client.get(
                "/api/research/study-information", headers=participant_headers
            ).json()
            enrolled = client.post(
                "/api/research/enroll",
                headers=participant_headers,
                json={
                    "access_code": "freeze-code",
                    "consent_version": information["version"],
                    "information_sheet_read": True,
                    "research_participation_accepted": True,
                    "data_processing_accepted": True,
                    "eligibility_version": eligibility_version(),
                    "age_confirmed": True,
                    "geography_confirmed": True,
                    "english_confirmed": True,
                    "other_criteria_confirmed": True,
                },
            ).json()
            participant_id = enrolled["participant_id"]
            session_id = client.post(
                "/api/sessions", headers=participant_headers
            ).json()["session_id"]
            client.post(
                "/api/chat", headers=participant_headers,
                json={"session_id": session_id, "message": "private frozen wording"},
            )

            researcher_headers = auth(client, "freeze-researcher@example.com")
            lifecycle = client.put(
                "/api/research/lifecycle", headers=researcher_headers,
                json={"start_date": "2026-01-01", "end_date": "2026-01-31"},
            )
            assert lifecycle.status_code == 200
            reviewed = client.patch(
                f"/api/research/participants/{participant_id}",
                headers=researcher_headers,
                json={"excluded": False, "exclusion_reason": "", "data_quality_notes": "Audio unavailable; text task valid."},
            )
            assert reviewed.status_code == 200
            frozen = client.post(
                "/api/research/freeze", headers=researcher_headers,
                json={"confirm_freeze": True},
            )
            assert frozen.status_code == 200
            manifest = frozen.json()
            assert manifest["schema_version"] == "affectlab-frozen-dataset-v1"
            assert manifest["record_count"] == 1
            assert len(manifest["sha256"]) == 64

            export = client.get("/api/research/export.csv", headers=researcher_headers)
            assert export.headers["x-content-sha256"] == manifest["sha256"]
            assert "P0001" in export.text
            assert participant_id not in export.text
            assert "private frozen wording" not in export.text
            assert client.patch(
                f"/api/research/participants/{participant_id}",
                headers=researcher_headers,
                json={"excluded": True, "exclusion_reason": "late", "data_quality_notes": ""},
            ).status_code == 409
            assert client.put(
                "/api/research/lifecycle", headers=researcher_headers,
                json={"start_date": "2026-01-01", "end_date": "2026-02-01"},
            ).status_code == 409
    finally:
        (
            settings.researcher_emails,
            settings.pilot_access_code,
            settings.study_protocol_version,
        ) = previous


def test_password_reset_is_generic_single_use_and_changes_credentials() -> None:
    with TestClient(app) as client:
        auth(client, "reset@example.com")
        unknown = client.post(
            "/api/auth/forgot-password", json={"email": "unknown@example.com"}
        )
        requested = client.post(
            "/api/auth/forgot-password", json={"email": "reset@example.com"}
        )
        assert unknown.status_code == requested.status_code == 202
        assert unknown.json() == requested.json()
        token = capturing_email.reset_tokens["reset@example.com"]
        reset = client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "replacement-password"},
        )
        assert reset.status_code == 204
        assert client.post(
            "/api/auth/login",
            json={"email": "reset@example.com", "password": "long-test-password"},
        ).status_code == 401
        assert client.post(
            "/api/auth/login",
            json={"email": "reset@example.com", "password": "replacement-password"},
        ).status_code == 200
        assert client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "another-password"},
        ).status_code == 400


def test_research_questionnaires_and_export_exclude_identity_and_conversation_text() -> None:
    previous_code = settings.pilot_access_code
    settings.pilot_access_code = "research-export-code"
    try:
        with TestClient(app) as client:
            headers = auth(client, "research@example.com")
            version = client.get(
                "/api/research/study-information", headers=headers
            ).json()["version"]
            enrolled = client.post(
                "/api/research/enroll",
                headers=headers,
                json={
                    "access_code": "research-export-code",
                    "consent_version": version,
                    "information_sheet_read": True,
                    "research_participation_accepted": True,
                    "data_processing_accepted": True,
                    "eligibility_version": eligibility_version(),
                    "age_confirmed": True,
                    "geography_confirmed": True,
                    "english_confirmed": True,
                    "other_criteria_confirmed": True,
                },
            )
            assert enrolled.status_code == 200
            session_id = client.post("/api/sessions", headers=headers).json()["session_id"]
            pre = client.put(
                f"/api/sessions/{session_id}/questionnaires/pre",
                headers=headers,
                json={"confidence": 3, "anxiety": 6},
            )
            assert pre.status_code == 200
            client.post(
                "/api/chat",
                headers=headers,
                json={"session_id": session_id, "message": "private conversation wording"},
            )
            export = client.get("/api/auth/research-export", headers=headers)
            assert export.status_code == 200
            body = export.json()
            assert body["contains_conversation_text"] is False
            assert body["records"][0]["questionnaires"]["pre"]["anxiety"] == 6
            serialized = export.text
            assert "private conversation wording" not in serialized
            assert "research@example.com" not in serialized
    finally:
        settings.pilot_access_code = previous_code


def test_multimodal_endpoint_is_authenticated_and_explicitly_unavailable_by_default() -> None:
    app.dependency_overrides[get_multimodal_service] = lambda: MultimodalAffectService(
        False, "", "", "missing.json"
    )
    try:
        with TestClient(app) as client:
            assert client.post("/api/affect/multimodal", json={}).status_code == 401
            headers = auth(client, "multimodal@example.com")
            session_id = client.post("/api/sessions", headers=headers).json()["session_id"]
            response = client.post(
                "/api/affect/multimodal",
                headers=headers,
                json={"session_id": session_id, "message": "I feel tense", "audio_wav_base64": "d2F2"},
            )
            assert response.status_code == 503
            assert response.json()["detail"] == "Multimodal inference is not configured"
    finally:
        app.dependency_overrides.pop(get_multimodal_service, None)


def test_audio_transcription_is_authenticated_and_returns_transient_result() -> None:
    class FakeTranscription:
        available = True
        model = "test-transcriber"

        async def transcribe(self, audio: bytes):
            assert audio.startswith(b"RIFF")
            return TranscriptionResult("I need more time for this task.", self.model, 12)

    output = io.BytesIO()
    with wave.open(output, "wb") as recording:
        recording.setnchannels(1); recording.setsampwidth(2); recording.setframerate(16_000)
        recording.writeframes(b"\x00\x00" * 8_000)
    payload = base64.b64encode(output.getvalue()).decode()
    app.dependency_overrides[get_transcription_service] = lambda: FakeTranscription()
    try:
        with TestClient(app) as client:
            assert client.post("/api/audio/transcriptions", json={"audio_wav_base64": payload}).status_code == 401
            headers = auth(client, "voice@example.com")
            response = client.post("/api/audio/transcriptions", headers=headers, json={"audio_wav_base64": payload})
            assert response.status_code == 200
            assert response.json() == {"text": "I need more time for this task.", "model": "test-transcriber", "latency_ms": 12, "audio_persisted": False}
    finally:
        app.dependency_overrides.pop(get_transcription_service, None)
