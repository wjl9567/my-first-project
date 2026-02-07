"""审计日志：在关键操作后写入 audit_logs 表。"""
from typing import Optional

from sqlalchemy.orm import Session

from . import models


def log_audit(
    db: Session,
    actor_id: int,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    details: Optional[str] = None,
    *,
    do_commit: bool = True,
) -> None:
    """写入一条审计记录。action 建议格式：资源.操作，如 device.create、usage.export、auth.login。
    do_commit=False 时仅 add 不提交，由调用方统一 commit（用于与业务操作同事务）。"""
    entry = models.AuditLog(
        actor_id=actor_id,
        action=action[:64],
        target_type=target_type[:64] if target_type else None,
        target_id=target_id,
        details=details,
    )
    db.add(entry)
    if do_commit:
        db.commit()
