"""字典管理：使用类型、设备状态等，支持增删改、软删除、启用/停用。"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from . import models, schemas
from .auth import require_role
from .database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/dict", tags=["dict"])


@router.get("", response_model=List[schemas.DictItemRead])
def list_dict_items(
    dict_type: Optional[str] = Query(None, description="usage_type / device_status，不传返回全部类型"),
    include_inactive: bool = Query(False, description="是否包含已停用项"),
    include_deleted: bool = Query(False, description="是否包含已删除项（仅后台管理用）"),
    db: Session = Depends(get_db),
):
    """列表；前端下拉用时不传 include_deleted，只拿未删除且可选的项。"""
    q = db.query(models.DictItem)
    if dict_type:
        q = q.filter(models.DictItem.dict_type == dict_type)
    if not include_deleted:
        q = q.filter(models.DictItem.is_deleted.is_(False))
    if not include_inactive:
        q = q.filter(models.DictItem.is_active.is_(True))
    return q.order_by(models.DictItem.sort_order, models.DictItem.id).all()


@router.post("", response_model=schemas.DictItemRead, status_code=status.HTTP_201_CREATED)
def create_dict_item(
    payload: schemas.DictItemCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_role("device_admin", "sys_admin")),
):
    """新增字典项；同类型下编码不可与未删除项重复。"""
    if payload.dict_type not in ("usage_type", "device_status"):
        raise HTTPException(status_code=400, detail="dict_type 仅支持 usage_type / device_status")
    code_str = str(payload.code)
    existing = (
        db.query(models.DictItem)
        .filter(
            models.DictItem.dict_type == payload.dict_type,
            models.DictItem.code == code_str,
            models.DictItem.is_deleted.is_(False),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="该类型下编码已存在")
    item = models.DictItem(
        dict_type=payload.dict_type,
        code=code_str,
        label=payload.label.strip(),
        is_active=True,
        is_deleted=False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=schemas.DictItemRead)
def update_dict_item(
    item_id: int,
    payload: schemas.DictItemUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_role("device_admin", "sys_admin")),
):
    """更新显示名称或启用/停用。"""
    item = db.get(models.DictItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="字典项不存在")
    if item.is_deleted:
        raise HTTPException(status_code=400, detail="已删除项不可修改，可先恢复")
    if payload.label is not None:
        item.label = payload.label.strip()
    if payload.is_active is not None:
        item.is_active = payload.is_active
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_dict_item(
    item_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_role("device_admin", "sys_admin")),
):
    """软删除：仅打标识，不物理删除。"""
    item = db.get(models.DictItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="字典项不存在")
    item.is_deleted = True
    db.commit()


@router.post("/{item_id}/restore", response_model=schemas.DictItemRead)
def restore_dict_item(
    item_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_role("device_admin", "sys_admin")),
):
    """恢复已软删除的项。"""
    item = db.get(models.DictItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="字典项不存在")
    if not item.is_deleted:
        raise HTTPException(status_code=400, detail="该项未删除")
    item.is_deleted = False
    db.commit()
    db.refresh(item)
    return item
