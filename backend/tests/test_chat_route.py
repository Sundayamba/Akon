from fastapi.testclient import TestClient

from app.main import app
from app.services.llm_provider import LLMProviderError
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

def test_chat_creates_consent_first_study_note_candidate(monkeypatch) -> None:
    headers = auth_headers(
        client,
        email="study-note-flow@example.com",
        display_name="Study Note User",
    )

    def fake_generate_reply(
        message: str,
        safety_result: dict,
        memory_context: str | None = None,
    ) -> str:
        if "teach me dns" in message.lower():
            return (
                "DNS means Domain Name System. It translates readable domain names "
                "into IP addresses that computers use to find systems on a network. "
                "DNS commonly uses port 53 and is essential for normal web browsing."
            )

        return "Preparing the study note review."

    monkeypatch.setattr(
        "app.api.routes.chat.generate_akon_reply",
        fake_generate_reply,
    )

    lesson_response = client.post(
        "/chat/message",
        headers=headers,
        json={"message": "Teach me DNS so I will remember it."},
    )

    assert lesson_response.status_code == 200

    conversation_id = lesson_response.json()["conversation_id"]

    candidate_response = client.post(
        "/chat/message",
        headers=headers,
        json={
            "message": "Turn this lesson into a study note.",
            "conversation_id": conversation_id,
        },
    )

    assert candidate_response.status_code == 200

    data = candidate_response.json()

    assert len(data["memory_candidates"]) == 1
    assert data["memory_candidates"][0]["memory_type"] == "study_note"
    assert data["memory_candidates"][0]["source"] == "study_session_candidate"
    assert data["memory_candidates"][0]["consent_required"] is True
    assert data["memory_candidates"][0]["content"].startswith("DNS:")
    assert "Nothing has been saved yet" in data["reply"]

def test_conversation_history_contains_persisted_continuity_metadata(
    monkeypatch,
) -> None:
    headers = auth_headers(
        client,
        email="continuity-history@example.com",
        display_name="Continuity History",
    )

    def fake_generate_reply(
        message: str,
        safety_result: dict,
        memory_context: str | None = None,
    ) -> str:
        return "This is Akon's persisted continuity response for the history preview."

    monkeypatch.setattr(
        "app.api.routes.chat.generate_akon_reply",
        fake_generate_reply,
    )

    create_response = client.post(
        "/chat/message",
        headers=headers,
        json={"message": "Create a conversation continuity test."},
    )

    assert create_response.status_code == 200
    assert create_response.json()["user_message_id"]

    conversation_id = create_response.json()["conversation_id"]

    history_response = client.get(
        "/chat/conversations",
        headers=headers,
    )

    assert history_response.status_code == 200

    history_item = next(
        item
        for item in history_response.json()
        if item["id"] == conversation_id
    )

    assert history_item["message_count"] == 2
    assert history_item["last_message_role"] == "assistant"
    assert "persisted continuity response" in history_item["last_message_preview"]
    assert history_item["last_message_at"] is not None


def test_existing_conversation_context_is_passed_to_next_reply(
    monkeypatch,
) -> None:
    headers = auth_headers(
        client,
        email="conversation-context@example.com",
        display_name="Conversation Context",
    )

    captured_contexts: list[str | None] = []

    def fake_generate_reply(
        message: str,
        safety_result: dict,
        memory_context: str | None = None,
    ) -> str:
        captured_contexts.append(memory_context)
        return "Context-aware response."

    monkeypatch.setattr(
        "app.api.routes.chat.generate_akon_reply",
        fake_generate_reply,
    )

    first_response = client.post(
        "/chat/message",
        headers=headers,
        json={"message": "My project codename is Horizon."},
    )

    assert first_response.status_code == 200

    conversation_id = first_response.json()["conversation_id"]

    second_response = client.post(
        "/chat/message",
        headers=headers,
        json={
            "message": "What project codename did I mention?",
            "conversation_id": conversation_id,
        },
    )

    assert second_response.status_code == 200
    assert captured_contexts[-1] is not None
    assert "Horizon" in captured_contexts[-1]


def test_failed_ai_request_does_not_create_phantom_conversation(
    monkeypatch,
) -> None:
    headers = auth_headers(
        client,
        email="failed-continuity@example.com",
        display_name="Failed Continuity",
    )

    before_response = client.get(
        "/chat/conversations",
        headers=headers,
    )

    assert before_response.status_code == 200

    before_ids = {
        item["id"]
        for item in before_response.json()
    }

    def fail_generate_reply(
        message: str,
        safety_result: dict,
        memory_context: str | None = None,
    ) -> str:
        raise LLMProviderError("Provider unavailable.")

    monkeypatch.setattr(
        "app.api.routes.chat.generate_akon_reply",
        fail_generate_reply,
    )

    failed_response = client.post(
        "/chat/message",
        headers=headers,
        json={"message": "This message must not create an empty conversation."},
    )

    assert failed_response.status_code == 503

    after_response = client.get(
        "/chat/conversations",
        headers=headers,
    )

    assert after_response.status_code == 200

    after_ids = {
        item["id"]
        for item in after_response.json()
    }

    assert after_ids == before_ids

def test_chat_response_reports_used_memories(
    monkeypatch,
) -> None:
    headers = auth_headers(
        client,
        email="used-memory@example.com",
        display_name="Used Memory",
    )

    memory_response = client.post(
        "/memory",
        headers=headers,
        json={
            "memory_type": "goal",
            "content": "User wants to become a cybersecurity product builder.",
            "source": "manual",
            "confidence": "high",
            "sensitivity": "low",
            "consent_state": "explicit",
        },
    )

    assert memory_response.status_code == 201
    captured_contexts: list[str | None] = []

    def fake_generate_reply(
        message: str,
        safety_result: dict,
        memory_context: str | None = None,
    ) -> str:
        captured_contexts.append(memory_context)
        return "You want to become a cybersecurity product builder."

    monkeypatch.setattr(
        "app.api.routes.chat.generate_akon_reply",
        fake_generate_reply,
    )

    response = client.post(
        "/chat/message",
        headers=headers,
        json={
            "message": "What do you remember about my cybersecurity goal?",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert captured_contexts[-1] is not None
    assert "cybersecurity product builder" in captured_contexts[-1]
    assert len(data["used_memories"]) == 1
    assert data["used_memories"][0]["id"] == memory_response.json()["id"]
    assert data["used_memories"][0]["relevance_score"] > 0
    assert data["used_memories"][0]["reasons"]
