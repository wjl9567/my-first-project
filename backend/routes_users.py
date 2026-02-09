"""管理端用户列表与统计（仅管理员可访问）。"""
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import get_current_user, require_role
from .database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/count")
def count_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("device_admin", "sys_admin")),
):
    """返回用户总数，用于工作台统计。"""
    total = db.query(models.User).count()
    return {"total": total}


@router.get("", response_model=List[schemas.UserListRead])
def list_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("device_admin", "sys_admin")),
):
    """分页返回用户列表（用户名、姓名、角色、科室、创建时间）。"""
    rows = (
        db.query(models.User)
        .order_by(models.User.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        schemas.UserListRead(
            id=u.id,
            username=u.username,
            wx_userid=u.wx_userid,
            real_name=u.real_name or "",
            role=u.role or "user",
            dept=u.dept,
            created_at=u.created_at,
        )
        for u in rows
    ]
