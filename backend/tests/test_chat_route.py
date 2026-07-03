from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_headers


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "akon-api",
    }


def test_chat_message_requires_auth() -> None:
    response = client.post(
        "/chat/message",
        json={"message": "I feel overwhelmed."},
    )

    assert response.status_code in {401, 403}


def test_chat_message_returns_reply() -> None:
    headers = auth_headers(client)

    response = client.post(
        "/chat/message",
        headers=headers,
        json={"message": "I feel overwhelmed and I do not know what to do next."},
    )

    assert response.status_code == 200

    data = response.json()

    assert "reply" in data
    assert data["safety_level"] == "S1"
    assert data["detected_emotion"] == "overwhelmed"
    assert "conversation_id" in data
    assert "memory_candidates" in data
    assert isinstance(data["memory_candidates"], list)
    assert "stress or overwhelm" in data["reply"]
    assert "One small step" in data["reply"]
    assert "I am here with you" in data["reply"]


def test_chat_message_returns_memory_candidate() -> None:
    headers = auth_headers(client)

    response = client.post(
        "/chat/message",
        headers=headers,
        json={"message": "I prefer direct step-by-step guidance."},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["safety_level"] == "S0"
    assert len(data["memory_candidates"]) >= 1
    assert data["memory_candidates"][0]["memory_type"] == "preference"
    assert data["memory_candidates"][0]["consent_required"] is True


def test_chat_message_avoids_noisy_memory_candidate_for_one_off_task() -> None:
    headers = auth_headers(client)

    response = client.post(
        "/chat/message",
        headers=headers,
        json={"message": "Can you teach me networking basics step by step?"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["safety_level"] == "S0"
    assert data["memory_candidates"] == []


def test_crisis_message_does_not_return_memory_candidate() -> None:
    headers = auth_headers(client)

    response = client.post(
        "/chat/message",
        headers=headers,
        json={"message": "I want to kill myself."},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["safety_level"] == "S4"
    assert data["memory_candidates"] == []


def test_chat_message_rejects_empty_message() -> None:
    headers = auth_headers(client)

    response = client.post(
        "/chat/message",
        headers=headers,
        json={"message": ""},
    )

    assert response.status_code == 422


def test_conversation_title_is_professional_for_writing_request() -> None:
    headers = auth_headers(client)

    create_response = client.post(
        "/chat/message",
        headers=headers,
        json={
            "message": "Write a professional announcement to my team about workplace discipline.",
        },
    )

    assert create_response.status_code == 200

    conversation_id = create_response.json()["conversation_id"]

    detail_response = client.get(
        f"/chat/conversations/{conversation_id}",
        headers=headers,
    )

    assert detail_response.status_code == 200

    assert detail_response.json()["title"] == "Professional announcement"


def test_list_conversations_returns_list() -> None:
    headers = auth_headers(client)

    client.post(
        "/chat/message",
        headers=headers,
        json={"message": "Hello Akon, help me plan my day."},
    )

    response = client.get(
        "/chat/conversations",
        headers=headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_conversation_returns_messages() -> None:
    headers = auth_headers(client)

    create_response = client.post(
        "/chat/message",
        headers=headers,
        json={"message": "I am hopeful things will get better."},
    )

    assert create_response.status_code == 200
    assert create_response.json()["detected_emotion"] == "hopeful"

    conversation_id = create_response.json()["conversation_id"]

    detail_response = client.get(
        f"/chat/conversations/{conversation_id}",
        headers=headers,
    )

    assert detail_response.status_code == 200

    data = detail_response.json()

    assert data["id"] == conversation_id
    assert "messages" in data
    assert len(data["messages"]) >= 2

    roles = [message["role"] for message in data["messages"]]

    assert "user" in roles
    assert "assistant" in roles
    assert all(message["detected_emotion"] == "hopeful" for message in data["messages"])


def test_get_unknown_conversation_returns_404() -> None:
    headers = auth_headers(client)

    response = client.get(
        "/chat/conversations/unknown-conversation-id",
        headers=headers,
    )

    assert response.status_code == 404


def test_user_cannot_access_another_users_conversation() -> None:
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

    create_response = client.post(
        "/chat/message",
        headers=user_one_headers,
        json={"message": "This is user one's private conversation."},
    )

    assert create_response.status_code == 200

    conversation_id = create_response.json()["conversation_id"]

    unauthorized_response = client.get(
        f"/chat/conversations/{conversation_id}",
        headers=user_two_headers,
    )

    assert unauthorized_response.status_code == 404