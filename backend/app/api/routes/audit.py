from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.services.auth_service import get_current_user

router = APIRouter()


def _to_audit_response(audit_log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=audit_log.id,
        actor_user_id=audit_log.actor_user_id,
        action=audit_log.action,
        entity_type=audit_log.entity_type,
        entity_id=audit_log.entity_id,
        risk_level=audit_log.risk_level,
        source=audit_log.source,
        details=audit_log.details,
        created_at=audit_log.created_at,
    )


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    audit_logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.actor_user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    ).all()

    return [_to_audit_response(audit_log) for audit_log in audit_logs]


@router.get("/{audit_id}", response_model=AuditLogResponse)
def get_audit_log(
    audit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuditLogResponse:
    audit_log = db.get(AuditLog, audit_id)

    if audit_log is None or audit_log.actor_user_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Audit log not found.",
        )

    return _to_audit_response(audit_log)