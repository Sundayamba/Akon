from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.services.audit_service import create_audit_log
from tests.helpers import auth_headers, login_user, register_user


client = TestClient(app)


def test_audit_route_requires_auth() -> None:
    response = client.get("/audit")

    assert response.status_code in {401, 403}


def test_list_audit_logs_returns_list() -> None:
    headers = auth_headers(client)

    response = client.get(
        "/audit",
        headers=headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_created_audit_log_can_be_listed_for_owner() -> None:
    user = register_user(
        client,
        email="owner@example.com",
        display_name="Owner",
    )

    login_response = login_user(
        client,
        email="owner@example.com",
    )

    headers = {
        "Authorization": f"Bearer {login_response['access_token']}",
    }

    with SessionLocal() as db:
        create_audit_log(
            db,
            action="test.audit.created",
            entity_type="test",
            entity_id="test-entity-id",
            actor_user_id=user["id"],
            risk_level="low",
            source="test",
            details={
                "message": "Audit test log.",
            },
        )
        db.commit()

    response = client.get(
        "/audit",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    actions = [audit_log["action"] for audit_log in data]

    assert "test.audit.created" in actions

    audit_log = next(
        audit_log for audit_log in data if audit_log["action"] == "test.audit.created"
    )

    assert audit_log["actor_user_id"] == user["id"]
    assert audit_log["entity_type"] == "test"
    assert audit_log["entity_id"] == "test-entity-id"
    assert audit_log["risk_level"] == "low"
    assert audit_log["source"] == "test"
    assert audit_log["details"]["message"] == "Audit test log."


def test_get_audit_log_by_id_for_owner() -> None:
    user = register_user(
        client,
        email="owner@example.com",
        display_name="Owner",
    )

    login_response = login_user(
        client,
        email="owner@example.com",
    )

    headers = {
        "Authorization": f"Bearer {login_response['access_token']}",
    }

    with SessionLocal() as db:
        audit_log = create_audit_log(
            db,
            action="test.audit.read",
            entity_type="test",
            entity_id="test-entity-id",
            actor_user_id=user["id"],
            risk_level="low",
            source="test",
            details=None,
        )
        db.commit()
        db.refresh(audit_log)

        audit_id = audit_log.id

    response = client.get(
        f"/audit/{audit_id}",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == audit_id
    assert data["actor_user_id"] == user["id"]
    assert data["action"] == "test.audit.read"


def test_get_unknown_audit_log_returns_404() -> None:
    headers = auth_headers(client)

    response = client.get(
        "/audit/unknown-audit-id",
        headers=headers,
    )

    assert response.status_code == 404


def test_user_cannot_access_another_users_audit_log() -> None:
    user_one = register_user(
        client,
        email="user-one@example.com",
        display_name="User One",
    )

    user_two_headers = auth_headers(
        client,
        email="user-two@example.com",
        display_name="User Two",
    )

    with SessionLocal() as db:
        audit_log = create_audit_log(
            db,
            action="test.audit.private",
            entity_type="test",
            entity_id="test-entity-id",
            actor_user_id=user_one["id"],
            risk_level="low",
            source="test",
            details=None,
        )
        db.commit()
        db.refresh(audit_log)

        audit_id = audit_log.id

    response = client.get(
        f"/audit/{audit_id}",
        headers=user_two_headers,
    )

    assert response.status_code == 404