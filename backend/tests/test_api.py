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

    async def send_verification(self, recipient: str, preferred_name: str, token: str) -> None:
        self.tokens[recipient] = token


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
        response = client.post("/api/chat", headers=headers, json={"session_id": session_id, "message": "I'm scared they will think I'm incompetent"})
        assert response.status_code == 200
        assert response.json()["decision"]["strategy"] == "validate_then_reframe"
        start = client.post(f"/api/sessions/{session_id}/roleplay", headers=headers, json={"scenario_id": "workload", "difficulty": "beginner"})
        assert start.status_code == 200
        reply = client.post("/api/chat", headers=headers, json={"session_id": session_id, "message": "I need you to prioritise the deadline because it is this week"}).json()
        assert reply["roleplay"]["status"] == "completed"
        assert reply["feedback"]["metrics"]


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
