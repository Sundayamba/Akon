from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import auth_headers


client = TestClient(app)


def _find_action(audit_logs: list[dict], action: str) -> dict:
    return next(audit_log for audit_log in audit_logs if audit_log["action"] == action)


def test_chat_message_creates_audit_log() -> None:
    headers = auth_headers(client)

    chat_response = client.post(
        "/chat/message",
        headers=headers,
        json={
            "message": "I feel overwhelmed and need guidance.",
        },
    )

    assert chat_response.status_code == 200

    conversation_id = chat_response.json()["conversation_id"]

    audit_response = client.get(
        "/audit",
        headers=headers,
    )

    assert audit_response.status_code == 200

    audit_logs = audit_response.json()

    audit_log = _find_action(
        audit_logs,
        "chat.message.created",
    )

    assert audit_log["entity_type"] == "conversation"
    assert audit_log["entity_id"] == conversation_id
    assert audit_log["actor_user_id"] is not None
    assert audit_log["risk_level"] == "medium"
    assert audit_log["details"]["safety_level"] == "S1"
    assert audit_log["details"]["detected_emotion"] == "overwhelmed"
    assert audit_log["details"]["memory_candidate_count"] >= 0
    assert "message_length" in audit_log["details"]
    assert "user_message_id" in audit_log["details"]
    assert "assistant_message_id" in audit_log["details"]


def test_crisis_chat_message_creates_critical_audit_log() -> None:
    headers = auth_headers(client)

    chat_response = client.post(
        "/chat/message",
        headers=headers,
        json={
            "message": "I want to kill myself.",
        },
    )

    assert chat_response.status_code == 200

    audit_response = client.get(
        "/audit",
        headers=headers,
    )

    assert audit_response.status_code == 200

    audit_logs = audit_response.json()

    audit_log = _find_action(
        audit_logs,
        "chat.message.created",
    )

    assert audit_log["risk_level"] == "critical"
    assert audit_log["details"]["safety_level"] == "S4"


def test_create_memory_creates_audit_log_without_content_leak() -> None:
    headers = auth_headers(client)
    memory_content = "User prefers direct, step-by-step guidance."

    memory_response = client.post(
        "/memory",
        headers=headers,
        json={
            "memory_type": "preference",
            "content": memory_content,
            "source": "manual",
            "confidence": "high",
            "sensitivity": "low",
            "consent_state": "explicit",
        },
    )

    assert memory_response.status_code == 201

    memory_id = memory_response.json()["id"]

    audit_response = client.get(
        "/audit",
        headers=headers,
    )

    assert audit_response.status_code == 200

    audit_logs = audit_response.json()

    audit_log = _find_action(
        audit_logs,
        "memory.created",
    )

    assert audit_log["entity_type"] == "memory"
    assert audit_log["entity_id"] == memory_id
    assert audit_log["actor_user_id"] is not None
    assert audit_log["details"]["memory_type"] == "preference"
    assert audit_log["details"]["content_length"] == len(memory_content)
    assert memory_content not in str(audit_log["details"])


def test_confirm_memory_candidate_creates_audit_log() -> None:
    headers = auth_headers(client)

    response = client.post(
        "/memory/confirm-candidate",
        headers=headers,
        json={
            "memory_type": "goal",
            "content": "User wants to build Akon safely.",
            "source": "chat_candidate",
            "confidence": "medium",
            "sensitivity": "low",
            "consent_required": True,
            "user_confirmed": True,
        },
    )

    assert response.status_code == 201

    audit_response = client.get(
        "/audit",
        headers=headers,
    )

    audit_logs = audit_response.json()

    audit_log = _find_action(
        audit_logs,
        "memory.candidate.confirmed",
    )

    assert audit_log["details"]["consent_required"] is True
    assert audit_log["details"]["user_confirmed"] is True


def test_update_memory_creates_audit_log() -> None:
    headers = auth_headers(client)

    create_response = client.post(
        "/memory",
        headers=headers,
        json={
            "memory_type": "preference",
            "content": "User likes short answers.",
            "source": "manual",
            "confidence": "medium",
            "sensitivity": "low",
            "consent_state": "explicit",
        },
    )

    memory_id = create_response.json()["id"]

    update_response = client.patch(
        f"/memory/{memory_id}",
        headers=headers,
        json={
            "content": "User prefers concise but complete answers.",
            "confidence": "high",
        },
    )

    assert update_response.status_code == 200

    audit_response = client.get(
        "/audit",
        headers=headers,
    )

    audit_logs = audit_response.json()

    actions = [audit_log["action"] for audit_log in audit_logs]

    assert "memory.created" in actions
    assert "memory.updated" in actions

    update_audit = _find_action(
        audit_logs,
        "memory.updated",
    )

    assert update_audit["entity_id"] == memory_id
    assert update_audit["details"]["updated_fields"] == ["confidence", "content"]


def test_revoke_memory_creates_audit_log() -> None:
    headers = auth_headers(client)

    create_response = client.post(
        "/memory",
        headers=headers,
        json={
            "memory_type": "preference",
            "content": "User prefers motivational guidance.",
            "source": "manual",
            "confidence": "medium",
            "sensitivity": "low",
            "consent_state": "explicit",
        },
    )

    memory_id = create_response.json()["id"]

    revoke_response = client.post(
        f"/memory/{memory_id}/revoke",
        headers=headers,
    )

    assert revoke_response.status_code == 200

    audit_response = client.get(
        "/audit",
        headers=headers,
    )

    audit_logs = audit_response.json()

    actions = [audit_log["action"] for audit_log in audit_logs]

    assert "memory.created" in actions
    assert "memory.revoked" in actions


def test_delete_memory_creates_audit_log() -> None:
    headers = auth_headers(client)

    create_response = client.post(
        "/memory",
        headers=headers,
        json={
            "memory_type": "constraint",
            "content": "User has limited time for development sessions.",
            "source": "manual",
            "confidence": "medium",
            "sensitivity": "low",
            "consent_state": "explicit",
        },
    )

    memory_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/memory/{memory_id}",
        headers=headers,
    )

    assert delete_response.status_code == 204

    audit_response = client.get(
        "/audit",
        headers=headers,
    )

    audit_logs = audit_response.json()

    actions = [audit_log["action"] for audit_log in audit_logs]

    assert "memory.created" in actions
    assert "memory.deleted" in actions


def test_clear_memories_creates_audit_log() -> None:
    headers = auth_headers(client)

    client.post(
        "/memory",
        headers=headers,
        json={
            "memory_type": "goal",
            "content": "User wants to build Akon carefully.",
            "source": "manual",
            "confidence": "medium",
            "sensitivity": "low",
            "consent_state": "explicit",
        },
    )

    clear_response = client.delete(
        "/memory",
        headers=headers,
    )

    assert clear_response.status_code == 204

    audit_response = client.get(
        "/audit",
        headers=headers,
    )

    audit_logs = audit_response.json()

    actions = [audit_log["action"] for audit_log in audit_logs]

    assert "memory.created" in actions
    assert "memory.cleared" in actions

    clear_audit = _find_action(
        audit_logs,
        "memory.cleared",
    )

    assert clear_audit["details"]["memory_count"] == 1
