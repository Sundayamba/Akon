from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.services.audit_service import create_audit_log


client = TestClient(app)


def test_list_audit_logs_returns_list() -> None:
    response = client.get("/audit")

    assert response.status_code == 200
    assert response.json() == []


def test_created_audit_log_can_be_listed() -> None:
    with SessionLocal() as db:
        create_audit_log(
            db,
            action="test.audit.created",
            entity_type="test",
            entity_id="test-entity-id",
            risk_level="low",
            source="test",
            details={
                "message": "Audit test log.",
            },
        )
        db.commit()

    response = client.get("/audit")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["action"] == "test.audit.created"
    assert data[0]["entity_type"] == "test"
    assert data[0]["entity_id"] == "test-entity-id"
    assert data[0]["risk_level"] == "low"
    assert data[0]["source"] == "test"
    assert data[0]["details"]["message"] == "Audit test log."


def test_get_audit_log_by_id() -> None:
    with SessionLocal() as db:
        audit_log = create_audit_log(
            db,
            action="test.audit.read",
            entity_type="test",
            entity_id="test-entity-id",
            risk_level="low",
            source="test",
            details=None,
        )
        db.commit()
        db.refresh(audit_log)

        audit_id = audit_log.id

    response = client.get(f"/audit/{audit_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == audit_id
    assert data["action"] == "test.audit.read"


def test_get_unknown_audit_log_returns_404() -> None:
    response = client.get("/audit/unknown-audit-id")

    assert response.status_code == 404