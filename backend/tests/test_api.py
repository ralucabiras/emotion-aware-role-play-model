from fastapi.testclient import TestClient

from app.main import app


def auth(client: TestClient, email: str = "user@example.com") -> dict[str, str]:
    result = client.post("/api/auth/register", json={"email": email, "password": "long-test-password", "consent": True})
    assert result.status_code == 201
    return {"Authorization": f"Bearer {result.json()['access_token']}"}


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


def test_multimodal_endpoint_is_authenticated_and_explicitly_unavailable_by_default() -> None:
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
