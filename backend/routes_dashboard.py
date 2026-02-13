"""工作台统计：设备数、用户数、使用记录总数及今日/本周/本月登记量。"""
from datetime import date, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from . import models
from .auth import get_current_user_optional, require_role
from .database import get_db
from .time_utils import china_today
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _china_week_range() -> tuple[date, date]:
    """中国时区本周一与本周日。"""
    today = china_today()
    weekday = today.weekday()  # 0=周一, 6=周日
    monday = today - timedelta(days=weekday)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _china_month_range() -> tuple[date, date]:
    """中国时区本月首日与末日。"""
    today = china_today()
    first = today.replace(day=1)
    next_month = first + timedelta(days=32)
    last = (next_month.replace(day=1)) - timedelta(days=1)
    return first, last


@router.get("/stats", response_model=Dict[str, Any])
def get_dashboard_stats(
    db: Session = Depends(get_db),
    _user=Depends(require_role("device_admin", "sys_admin")),
):
    """工作台统计：设备/用户/使用记录总数，及今日、本周、本月登记量（按登记日期）。"""
    today = china_today()
    week_start, week_end = _china_week_range()
    month_start, month_end = _china_month_range()

    # 设备数（复用 devices 查询逻辑）
    from .routes_devices import _devices_query

    q_all = _devices_query(db, None, None, True, True, False, False, True)
    q_active = _devices_query(db, None, None, False, False, False, False, True)
    q_inactive = _devices_query(db, None, None, False, False, False, True, True)
    q_deleted = _devices_query(db, None, None, False, False, True, False, True)

    devices_total = q_all.count()
    devices_active = q_active.count()
    devices_inactive = q_inactive.count()
    devices_deleted = q_deleted.count()

    # 用户数
    users_total = db.query(models.User).filter(models.User.is_active.is_(True)).count()

    # 使用记录：总数 + 今日/本周/本月（按 registration_date，不含已撤销）
    base = db.query(models.UsageRecord).filter(models.UsageRecord.is_deleted.is_(False))
    usage_total = base.count()
    usage_today = base.filter(
        models.UsageRecord.registration_date >= today,
        models.UsageRecord.registration_date <= today,
    ).count()
    usage_week = base.filter(
        models.UsageRecord.registration_date >= week_start,
        models.UsageRecord.registration_date <= week_end,
    ).count()
    usage_month = base.filter(
        models.UsageRecord.registration_date >= month_start,
        models.UsageRecord.registration_date <= month_end,
    ).count()

    return {
        "devices_total": devices_total,
        "devices_active": devices_active,
        "devices_inactive": devices_inactive,
        "devices_deleted": devices_deleted,
        "users_total": users_total,
        "usage_total": usage_total,
        "usage_today": usage_today,
        "usage_week": usage_week,
        "usage_month": usage_month,
    }
