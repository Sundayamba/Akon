from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogResponse

router = APIRouter()


def _to_audit_response(audit_log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=audit_log.id,
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
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    audit_logs = db.scalars(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    ).all()

    return [_to_audit_response(audit_log) for audit_log in audit_logs]


@router.get("/{audit_id}", response_model=AuditLogResponse)
def get_audit_log(
    audit_id: str,
    db: Session = Depends(get_db),
) -> AuditLogResponse:
    audit_log = db.get(AuditLog, audit_id)

    if audit_log is None:
        raise HTTPException(
            status_code=404,
            detail="Audit log not found.",
        )

    return _to_audit_response(audit_log)