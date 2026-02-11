from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wx_userid: Mapped[Optional[str]] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )  # 企微用户；本地管理员可为空
    username: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )  # 本地管理员登录名
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # 仅本地管理员使用
    real_name: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(32), default="user")  # user / device_admin / sys_admin
    dept: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)  # 停用/启用
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="user"
    )


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    dept: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="1"
    )  # 设备状态字典编码（数字字符串，如 "1" 可用）
    qr_value: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, unique=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # 软删除标识
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="device"
    )

    __table_args__ = (
        Index("ix_devices_active_deleted", "is_active", "is_deleted"),
    )


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_code: Mapped[str] = mapped_column(
        String(64), ForeignKey("devices.device_code"), index=True
    )  # 与 devices.device_code 同类型，统一存设备编号
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    usage_type: Mapped[str] = mapped_column(
        String(32)
    )  # 使用类型字典编码（数字字符串，如 "1" 常规使用）
    dept_at_use: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    patient_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 简化：仅记录开始时间；维护登记时表示开机时间
    start_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    # 维护登记：关机时间
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 维护登记：登记日期（护士选择的那天），后台同时保留 created_at 为实际提交时间
    registration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    bed_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    id_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    patient_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    equipment_condition: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True
    )  # normal / abnormal
    daily_maintenance: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True
    )  # clean / disinfect
    terminal_disinfection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    photo_urls: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # 逗号分隔的 URL 列表

    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # 用户撤销（软删除）

    device: Mapped["Device"] = relationship(
        "Device", back_populates="usage_records"
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="usage_records"
    )

    __table_args__ = (
        Index("ix_usage_user_start", "user_id", "start_time"),
        Index("ix_usage_device_start", "device_code", "start_time"),
    )


class DictItem(Base):
    """字典项：使用类型、设备状态等；编码为数字且同类型内唯一，支持软删除与启用/停用。"""
    __tablename__ = "dict_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dict_type: Mapped[str] = mapped_column(String(32), index=True)  # usage_type / device_status
    code: Mapped[str] = mapped_column(String(32))  # 存数字字符串如 "1"；兼容旧库英文如 "routine"
    label: Mapped[str] = mapped_column(String(128))  # 显示名称
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # 软删除标识
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    actor: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[actor_id]
    )

