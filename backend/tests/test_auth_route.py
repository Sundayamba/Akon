from sqlalchemy import select
from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.models.audit import AuditLog


client = TestClient(app)


def test_register_user() -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "rex@example.com",
            "password": "strongpassword123",
            "display_name": "Rex",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "rex@example.com"
    assert data["display_name"] == "Rex"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email_returns_409() -> None:
    payload = {
        "email": "rex@example.com",
        "password": "strongpassword123",
        "display_name": "Rex",
    }

    first_response = client.post("/auth/register", json=payload)
    second_response = client.post("/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_login_user_returns_token() -> None:
    client.post(
        "/auth/register",
        json={
            "email": "rex@example.com",
            "password": "strongpassword123",
            "display_name": "Rex",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "rex@example.com",
            "password": "strongpassword123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert "access_token" in data
    assert data["user"]["email"] == "rex@example.com"


def test_login_with_wrong_password_returns_401() -> None:
    client.post(
        "/auth/register",
        json={
            "email": "rex@example.com",
            "password": "strongpassword123",
            "display_name": "Rex",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "rex@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401


def test_get_me_with_token() -> None:
    client.post(
        "/auth/register",
        json={
            "email": "rex@example.com",
            "password": "strongpassword123",
            "display_name": "Rex",
        },
    )

    login_response = client.post(
        "/auth/login",
        json={
            "email": "rex@example.com",
            "password": "strongpassword123",
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "rex@example.com"
    assert data["display_name"] == "Rex"


def test_get_me_without_token_returns_401_or_403() -> None:
    response = client.get("/auth/me")

    assert response.status_code in {401, 403}


def test_auth_events_create_audit_logs() -> None:
    register_response = client.post(
        "/auth/register",
        json={
            "email": "rex@example.com",
            "password": "strongpassword123",
            "display_name": "Rex",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": "rex@example.com",
            "password": "strongpassword123",
        },
    )

    assert login_response.status_code == 200

    failed_login_response = client.post(
        "/auth/login",
        json={
            "email": "rex@example.com",
            "password": "wrongpassword",
        },
    )

    assert failed_login_response.status_code == 401

    token = login_response.json()["access_token"]

    audit_response = client.get(
        "/audit",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert audit_response.status_code == 200

    visible_actions = [audit_log["action"] for audit_log in audit_response.json()]

    assert "auth.user.registered" in visible_actions
    assert "auth.login.succeeded" in visible_actions

    with SessionLocal() as db:
        all_audit_logs = db.scalars(select(AuditLog)).all()

    all_actions = [audit_log.action for audit_log in all_audit_logs]

    assert "auth.login.failed" in all_actions