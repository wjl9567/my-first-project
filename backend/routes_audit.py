"""审计日志查询 API，仅管理员可访问。"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .auth import require_role
from .database import get_db
from .time_utils import parse_naive_as_china_then_utc

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("", response_model=List[schemas.AuditLogRead])
def list_audit_logs(
    action: Optional[str] = Query(None, description="操作类型筛选，如 device.create"),
    actor_id: Optional[int] = Query(None, description="操作人 ID"),
    target_type: Optional[str] = Query(None, description="对象类型，如 device"),
    from_time: Optional[datetime] = Query(None, description="开始时间"),
    to_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(200, ge=1, le=500, description="最多返回条数"),
    db: Session = Depends(get_db),
    _user=Depends(require_role("device_admin", "sys_admin")),
):
    query = (
        db.query(models.AuditLog)
        .options(joinedload(models.AuditLog.actor))
        .order_by(models.AuditLog.created_at.desc())
    )
    if action:
        query = query.filter(models.AuditLog.action == action)
    if actor_id is not None:
        query = query.filter(models.AuditLog.actor_id == actor_id)
    if target_type:
        query = query.filter(models.AuditLog.target_type == target_type)
    if from_time:
        from_utc = parse_naive_as_china_then_utc(from_time)
        if from_utc:
            query = query.filter(models.AuditLog.created_at >= from_utc)
    if to_time:
        to_utc = parse_naive_as_china_then_utc(to_time)
        if to_utc:
            query = query.filter(models.AuditLog.created_at <= to_utc)
    rows = query.limit(limit).all()
    result = []
    for r in rows:
        target_code = None
        if r.target_type == "device" and r.target_id is not None:
            dev = db.query(models.Device).filter(
                models.Device.id == r.target_id
            ).first()
            if dev:
                target_code = dev.device_code
        item = schemas.AuditLogRead(
            id=r.id,
            actor_id=r.actor_id,
            actor_name=(r.actor.real_name or getattr(r.actor, "username", None)) if r.actor else None,
            action=r.action,
            target_type=r.target_type,
            target_id=r.target_id,
            target_code=target_code,
            details=r.details,
            created_at=r.created_at,
        )
        result.append(item)
    return result
