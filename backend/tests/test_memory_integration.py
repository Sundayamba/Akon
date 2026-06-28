from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_saved_memory_influences_chat_reply() -> None:
    memory_response = client.post(
        "/memory",
        json={
            "memory_type": "preference",
            "content": "User prefers direct, step-by-step guidance.",
            "source": "manual",
            "confidence": "high",
            "sensitivity": "low",
            "consent_state": "explicit",
        },
    )

    assert memory_response.status_code == 201

    chat_response = client.post(
        "/chat/message",
        json={
            "message": "I feel overwhelmed and need guidance.",
        },
    )

    assert chat_response.status_code == 200

    data = chat_response.json()

    assert data["safety_level"] == "S1"
    assert data["detected_emotion"] == "anxiety"
    assert "reply" in data
    assert "conversation_id" in data
    assert "memory_candidates" in data

    reply = data["reply"].lower()

    assert (
        "remember" in reply
        or "saved context" in reply
        or "taking into account" in reply
    )