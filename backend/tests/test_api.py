from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_chat_pipeline_tracks_emotion() -> None:
    session = client.post("/api/sessions").json()
    response = client.post(
        "/api/chat",
        json={"session_id": session["session_id"], "message": "I'm scared they will think I'm incompetent"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["emotion_state"]["dominant_emotion"] in {"anxiety", "shame"}
    assert body["decision"]["strategy"] == "validate_then_reframe"


def test_crisis_language_interrupts_normal_coaching() -> None:
    session_id = client.post("/api/sessions").json()["session_id"]
    body = client.post(
        "/api/chat", json={"session_id": session_id, "message": "I want to kill myself"}
    ).json()
    assert body["decision"]["strategy"] == "safety_escalation"
    assert "emergency" in body["turn"]["content"].lower()


def test_roleplay_starts_and_responds() -> None:
    session_id = client.post("/api/sessions").json()["session_id"]
    start = client.post(f"/api/sessions/{session_id}/roleplay", json={"scenario_id": "workload"})
    assert start.status_code == 200
    reply = client.post(
        "/api/chat", json={"session_id": session_id, "message": "I need help prioritising my deadlines"}
    ).json()
    assert reply["roleplay"]["turn"] == 1
