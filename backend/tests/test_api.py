import base64
import io
import wave

from fastapi.testclient import TestClient

from app.core.container import auth_service, get_multimodal_service, get_transcription_service
from app.main import app
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
    with TestClient(app) as client:
        headers = auth(client, "research@example.com")
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
        assert body["sessions"][0]["questionnaires"]["pre"]["anxiety"] == 6
        serialized = export.text
        assert "private conversation wording" not in serialized
        assert "research@example.com" not in serialized


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
