from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_memory() -> None:
    response = client.post(
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

    assert response.status_code == 201

    data = response.json()

    assert data["memory_type"] == "preference"
    assert data["content"] == "User prefers direct, step-by-step guidance."
    assert data["confidence"] == "high"
    assert data["consent_state"] == "explicit"
    assert "id" in data


def test_confirm_memory_candidate_saves_explicit_memory() -> None:
    response = client.post(
        "/memory/confirm-candidate",
        json={
            "memory_type": "preference",
            "content": "User prefers concise, direct guidance.",
            "source": "chat_candidate",
            "confidence": "medium",
            "sensitivity": "low",
            "consent_required": True,
            "user_confirmed": True,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["memory_type"] == "preference"
    assert data["content"] == "User prefers concise, direct guidance."
    assert data["source"] == "chat_candidate"
    assert data["consent_state"] == "explicit"


def test_confirm_memory_candidate_requires_user_confirmation() -> None:
    response = client.post(
        "/memory/confirm-candidate",
        json={
            "memory_type": "preference",
            "content": "User prefers concise, direct guidance.",
            "source": "chat_candidate",
            "confidence": "medium",
            "sensitivity": "low",
            "consent_required": True,
            "user_confirmed": False,
        },
    )

    assert response.status_code == 400


def test_list_memories() -> None:
    client.post(
        "/memory",
        json={
            "memory_type": "goal",
            "content": "User wants Akon to become a strong AI companion MVP.",
            "source": "manual",
            "confidence": "high",
            "sensitivity": "low",
            "consent_state": "explicit",
        },
    )

    response = client.get("/memory")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_memory_by_id() -> None:
    create_response = client.post(
        "/memory",
        json={
            "memory_type": "preference",
            "content": "User prefers structured guidance.",
            "source": "manual",
            "confidence": "high",
            "sensitivity": "low",
            "consent_state": "explicit",
        },
    )

    memory_id = create_response.json()["id"]

    response = client.get(f"/memory/{memory_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == memory_id
    assert data["memory_type"] == "preference"
    assert data["content"] == "User prefers structured guidance."


def test_get_unknown_memory_returns_404() -> None:
    response = client.get("/memory/unknown-memory-id")

    assert response.status_code == 404


def test_update_memory() -> None:
    create_response = client.post(
        "/memory",
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
        json={
            "content": "User prefers concise but complete answers.",
            "confidence": "high",
        },
    )

    assert update_response.status_code == 200

    data = update_response.json()

    assert data["id"] == memory_id
    assert data["content"] == "User prefers concise but complete answers."
    assert data["confidence"] == "high"


def test_revoke_memory() -> None:
    create_response = client.post(
        "/memory",
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

    revoke_response = client.post(f"/memory/{memory_id}/revoke")

    assert revoke_response.status_code == 200

    data = revoke_response.json()

    assert data["id"] == memory_id
    assert data["consent_state"] == "revoked"


def test_revoke_unknown_memory_returns_404() -> None:
    response = client.post("/memory/unknown-memory-id/revoke")

    assert response.status_code == 404


def test_delete_memory() -> None:
    create_response = client.post(
        "/memory",
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

    delete_response = client.delete(f"/memory/{memory_id}")

    assert delete_response.status_code == 204


def test_clear_all_memories() -> None:
    client.post(
        "/memory",
        json={
            "memory_type": "goal",
            "content": "User wants to build Akon carefully.",
            "source": "manual",
            "confidence": "medium",
            "sensitivity": "low",
            "consent_state": "explicit",
        },
    )

    delete_response = client.delete("/memory")

    assert delete_response.status_code == 204

    list_response = client.get("/memory")

    assert list_response.status_code == 200
    assert list_response.json() == []


def test_update_unknown_memory_returns_404() -> None:
    response = client.patch(
        "/memory/unknown-memory-id",
        json={
            "content": "This should not exist.",
        },
    )

    assert response.status_code == 404


def test_delete_unknown_memory_returns_404() -> None:
    response = client.delete("/memory/unknown-memory-id")

    assert response.status_code == 404