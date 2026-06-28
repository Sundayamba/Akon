from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str | None = None
    risk_level: str
    source: str
    details: dict[str, Any] | None = None
    created_at: datetime