from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "akon-api",
    }


def test_chat_message_returns_reply() -> None:
    response = client.post(
        "/chat/message",
        json={"message": "I feel overwhelmed and I do not know what to do next."},
    )

    assert response.status_code == 200

    data = response.json()

    assert "reply" in data
    assert data["safety_level"] == "S1"
    assert data["detected_emotion"] == "anxiety"
    assert "conversation_id" in data
    assert "memory_candidates" in data
    assert isinstance(data["memory_candidates"], list)


def test_chat_message_returns_memory_candidate() -> None:
    response = client.post(
        "/chat/message",
        json={"message": "I prefer direct step-by-step guidance."},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["safety_level"] == "S0"
    assert len(data["memory_candidates"]) >= 1
    assert data["memory_candidates"][0]["memory_type"] == "preference"
    assert data["memory_candidates"][0]["consent_required"] is True


def test_crisis_message_does_not_return_memory_candidate() -> None:
    response = client.post(
        "/chat/message",
        json={"message": "I want to kill myself."},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["safety_level"] == "S4"
    assert data["memory_candidates"] == []


def test_chat_message_rejects_empty_message() -> None:
    response = client.post(
        "/chat/message",
        json={"message": ""},
    )

    assert response.status_code == 422


def test_list_conversations_returns_list() -> None:
    client.post(
        "/chat/message",
        json={"message": "Hello Akon, help me plan my day."},
    )

    response = client.get("/chat/conversations")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_conversation_returns_messages() -> None:
    create_response = client.post(
        "/chat/message",
        json={"message": "I am excited about building Akon."},
    )

    assert create_response.status_code == 200

    conversation_id = create_response.json()["conversation_id"]

    detail_response = client.get(f"/chat/conversations/{conversation_id}")

    assert detail_response.status_code == 200

    data = detail_response.json()

    assert data["id"] == conversation_id
    assert "messages" in data
    assert len(data["messages"]) >= 2

    roles = [message["role"] for message in data["messages"]]

    assert "user" in roles
    assert "assistant" in roles


def test_get_unknown_conversation_returns_404() -> None:
    response = client.get("/chat/conversations/unknown-conversation-id")

    assert response.status_code == 404