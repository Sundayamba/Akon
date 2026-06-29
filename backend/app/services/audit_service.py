from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def create_audit_log(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    actor_user_id: str | None = None,
    risk_level: str = "low",
    source: str = "system",
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """
    Create an audit log entry.

    This function does not commit. The caller controls the transaction.
    """
    audit_log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        risk_level=risk_level,
        source=source,
        details=details,
    )

    db.add(audit_log)

    return audit_log