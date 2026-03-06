"""管理端用户列表与统计（仅管理员可访问）。"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models, schemas
from .audit import log_audit
from .auth import hash_password, truncate_password_for_bcrypt, require_role
from .database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])

_ALLOWED_ROLES = ("user", "device_admin", "sys_admin")


@router.post("", response_model=schemas.UserListRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("device_admin", "sys_admin")),
):
    """新增本地用户（用户名+密码）。设备管理员仅可创建普通用户；系统管理员可指定任意角色。"""
    if payload.role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="角色须为 user / device_admin / sys_admin")
    if current_user.role == "device_admin" and payload.role != "user":
        raise HTTPException(status_code=403, detail="设备管理员仅可创建普通用户")
    username = (payload.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="该用户名已存在")
    real_name = (payload.real_name or "").strip() or username
    plain = truncate_password_for_bcrypt(payload.password or "")
    if not plain:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    user = models.User(
        wx_userid=None,
        username=username,
        password_hash=hash_password(plain),
        real_name=real_name,
        role=payload.role,
        dept=(payload.dept or "").strip() or None,
        is_active=True,
    )
    db.add(user)
    db.flush()
    log_audit(db, current_user.id, "user.create", "user", user.id, details=username, do_commit=False)
    db.commit()
    db.refresh(user)
    return schemas.UserListRead(
        id=user.id,
        username=user.username,
        wx_userid=user.wx_userid,
        real_name=user.real_name or "",
        role=user.role or "user",
        dept=user.dept,
        is_active=getattr(user, "is_active", True),
        created_at=user.created_at,
    )


def _user_filter_query(db: Session, q: Optional[str]):
    """构建用户查询（可选按关键词模糊匹配工号/用户名、姓名、科室）。"""
    query = db.query(models.User)
    if q and q.strip():
        key = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.User.username.ilike(key),
                models.User.wx_userid.ilike(key),
                models.User.real_name.ilike(key),
                models.User.dept.ilike(key),
            )
        )
    return query


@router.get("/count")
def count_users(
    q: Optional[str] = Query(None, description="关键词：工号/用户名/姓名/科室，模糊匹配"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("device_admin", "sys_admin")),
):
    """返回用户总数（支持与列表一致的 q 筛选）。"""
    total = _user_filter_query(db, q).count()
    return {"total": total}


@router.get("", response_model=List[schemas.UserListRead])
def list_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None, description="关键词：工号/用户名/姓名/科室，模糊匹配"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("device_admin", "sys_admin")),
):
    """分页返回用户列表；支持 q 关键词模糊检索（工号/用户名、姓名、科室）。"""
    query = _user_filter_query(db, q)
    rows = (
        query
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
            is_active=getattr(u, "is_active", True),
            created_at=u.created_at,
        )
        for u in rows
    ]


@router.patch("/{user_id}/password")
def admin_update_user_password(
    user_id: int,
    payload: schemas.UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("sys_admin")),
):
    """系统管理员修改本地账号密码（仅对存在 username 的用户有意义）。"""
    u = db.get(models.User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not u.username:
        raise HTTPException(status_code=400, detail="该用户为企业微信账号，无本地用户名，无法修改密码")
    plain = truncate_password_for_bcrypt(payload.password or "")
    if not plain:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码不能为空")
    u.password_hash = hash_password(plain)
    db.commit()
    log_audit(db, current_user.id, "user.password_update", "user", u.id, details=f"reset:{u.username}")
    return {"ok": True}


@router.patch("/{user_id}/active")
def admin_update_user_active(
    user_id: int,
    payload: schemas.UserActiveUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("device_admin", "sys_admin")),
):
    """系统管理员停用/启用用户账号。管理员账号不可被停用。"""
    u = db.get(models.User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if u.id == current_user.id:
        raise HTTPException(status_code=400, detail="不可停用/启用当前登录账号")
    # 仅允许操作普通用户；管理员（device_admin/sys_admin）不可停用
    if (u.role or "user") in ("device_admin", "sys_admin"):
        raise HTTPException(status_code=400, detail="管理员账号不可停用")
    u.is_active = bool(payload.is_active)
    db.commit()
    log_audit(
        db,
        current_user.id,
        "user.active_update",
        "user",
        u.id,
        details=f"{'enable' if u.is_active else 'disable'}:{u.username or u.wx_userid or u.id}",
    )
    return {"ok": True, "is_active": u.is_active}


@router.patch("/{user_id}", response_model=schemas.UserListRead)
def admin_update_user_profile(
    user_id: int,
    payload: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("device_admin", "sys_admin")),
):
    """管理员修改用户信息（姓名、科室、角色、用户名）。"""
    u = db.get(models.User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    changes = []
    if payload.real_name is not None:
        name = payload.real_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="姓名不能为空")
        if name != (u.real_name or ""):
            u.real_name = name
            changes.append(f"real_name={name}")
    if payload.dept is not None:
        dept = payload.dept.strip() or None
        if dept != u.dept:
            u.dept = dept
            changes.append(f"dept={dept}")
    if payload.role is not None:
        role = payload.role.strip()
        if role not in _ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="角色须为 user / device_admin / sys_admin")
        if current_user.role == "device_admin" and role != "user":
            raise HTTPException(status_code=403, detail="设备管理员仅可设置普通用户角色")
        if u.id == current_user.id and role != current_user.role:
            raise HTTPException(status_code=400, detail="不可修改自己的角色")
        if role != (u.role or "user"):
            u.role = role
            changes.append(f"role={role}")
    if payload.username is not None:
        uname = payload.username.strip()
        if uname:
            existing = db.query(models.User).filter(
                models.User.username == uname, models.User.id != u.id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="该用户名已被其他用户使用")
        if uname != (u.username or ""):
            u.username = uname or None
            changes.append(f"username={uname}")
    if not changes:
        pass
    else:
        db.commit()
        db.refresh(u)
        log_audit(db, current_user.id, "user.profile_update", "user", u.id, details=";".join(changes))
    return schemas.UserListRead(
        id=u.id,
        username=u.username,
        wx_userid=u.wx_userid,
        real_name=u.real_name or "",
        role=u.role or "user",
        dept=u.dept,
        is_active=getattr(u, "is_active", True),
        created_at=u.created_at,
    )
