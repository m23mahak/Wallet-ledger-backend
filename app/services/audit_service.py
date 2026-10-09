"""Audit logging service."""
import json
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def record_audit(
    db: AsyncSession,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_id: Optional[int] = None,
    actor_email: Optional[str] = None,
    details: Optional[Any] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    details_str = None
    if details is not None:
        if isinstance(details, (dict, list)):
            details_str = json.dumps(details)
        else:
            details_str = str(details)

    log = AuditLog(
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details_str,
        ip_address=ip_address,
    )
    db.add(log)
    return log
