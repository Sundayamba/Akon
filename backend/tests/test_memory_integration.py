from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_headers


client = TestClient(app)


def test_saved_memory_influences_chat_reply() -> None:
    headers = auth_headers(client)

    memory_response = client.post(
        "/memory",
        headers=headers,
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
        headers=headers,
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


def test_user_memory_does_not_influence_another_user_chat() -> None:
    user_one_headers = auth_headers(
        client,
        email="user-one@example.com",
        display_name="User One",
    )

    user_two_headers = auth_headers(
        client,
        email="user-two@example.com",
        display_name="User Two",
    )

    memory_response = client.post(
        "/memory",
        headers=user_one_headers,
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
        headers=user_two_headers,
        json={
            "message": "I feel overwhelmed and need guidance.",
        },
    )

    assert chat_response.status_code == 200

    reply = chat_response.json()["reply"].lower()

    assert "remember" not in reply
    assert "saved context" not in reply
    assert "taking into account" not in reply