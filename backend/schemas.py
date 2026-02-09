from datetime import date, datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    wx_userid: Optional[str] = None
    real_name: str
    dept: Optional[str] = None
    role: str = "user"


class UserRead(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserListRead(BaseModel):
    """管理端用户列表项（含用户名）。"""
    id: int
    username: Optional[str] = None
    wx_userid: Optional[str] = None
    real_name: str
    role: str
    dept: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceBase(BaseModel):
    device_code: str = Field(..., description="设备内部编号，唯一")
    name: str
    dept: Optional[str] = None
    location: Optional[str] = None
    status: int = Field(1, description="设备状态字典编码（数字）")
    qr_value: Optional[str] = None
    is_active: bool = True


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    """部分更新：编号、名称、科室、位置、状态、启用、软删除标识"""
    device_code: Optional[str] = Field(None, max_length=64, description="修改时须保证唯一")
    name: Optional[str] = Field(None, max_length=128)
    dept: Optional[str] = Field(None, max_length=128)
    location: Optional[str] = Field(None, max_length=256)
    status: Optional[int] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None


class DeviceRead(DeviceBase):
    id: int
    is_deleted: bool = False
    created_at: datetime

    @field_validator("status", mode="before")
    @classmethod
    def status_to_int(cls, v: Union[str, int]) -> int:
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
        legacy = {"available": 1, "in_use": 2, "maintenance": 3, "fault": 4, "scrapped": 5}
        return legacy.get(v, 1)

    class Config:
        from_attributes = True


class UsageRecordBase(BaseModel):
    device_code: str = Field(..., description="设备编号，与 devices.device_code 一致")
    usage_type: int = Field(..., description="使用类型字典编码（数字）")
    dept_at_use: Optional[str] = None
    patient_id: Optional[str] = None
    note: Optional[str] = Field(None, max_length=500, description="备注，最多500字")
    start_time: Optional[datetime] = None
    photo_urls: Optional[List[str]] = None
    source: Optional[str] = None
    # 维护登记扩展字段
    registration_date: Optional[date] = Field(None, description="登记日期（护士选择的那天）")
    bed_number: Optional[str] = Field(None, max_length=32, description="床号")
    id_number: Optional[str] = Field(None, max_length=64, description="ID号")
    patient_name: Optional[str] = Field(None, max_length=64, description="姓名，选填")
    end_time: Optional[datetime] = Field(None, description="关机时间")
    equipment_condition: Optional[str] = Field(
        None, max_length=16, description="设备状况：normal 正常 / abnormal 异常"
    )
    daily_maintenance: Optional[str] = Field(
        None, max_length=16, description="日常保养：clean 清洁 / disinfect 消毒"
    )
    terminal_disinfection: Optional[str] = Field(None, max_length=500, description="终末消毒备注，选填")


class UsageRecordCreate(UsageRecordBase):
    @field_validator("usage_type", mode="before")
    @classmethod
    def usage_type_coerce(cls, v: Union[str, int, None]) -> int:
        """兼容前端未选或传空：默认 1（常规使用）。"""
        if v is None or v == "":
            return 1
        if isinstance(v, int) and not (isinstance(v, bool)):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return 1


class UsageRecordRead(UsageRecordBase):
    id: int
    user_id: int
    user_name: Optional[str] = None
    device_name: Optional[str] = None
    created_at: datetime
    is_deleted: bool = False

    @field_validator("usage_type", mode="before")
    @classmethod
    def usage_type_to_int(cls, v: Union[str, int]) -> int:
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
        # 兼容旧数据英文编码
        legacy = {"routine": 1, "borrow": 2, "maintenance": 3, "calibration": 4, "other": 5}
        return legacy.get(v, 0)

    class Config:
        from_attributes = True


class DictItemCreate(BaseModel):
    dict_type: str = Field(..., description="usage_type / device_status")
    code: int = Field(..., description="数字编码，同类型内唯一")
    label: str = Field(..., max_length=128)


class DictItemUpdate(BaseModel):
    label: Optional[str] = Field(None, max_length=128)
    is_active: Optional[bool] = None


class DictItemRead(BaseModel):
    id: int
    dict_type: str
    code: int
    label: str
    is_active: bool
    is_deleted: bool
    sort_order: int
    created_at: datetime

    @field_validator("code", mode="before")
    @classmethod
    def code_to_int(cls, v: Union[str, int]) -> int:
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
        # 兼容旧库英文编码
        legacy = {"routine": 1, "borrow": 2, "maintenance": 3, "calibration": 4, "other": 5,
                  "available": 1, "in_use": 2, "fault": 4, "scrapped": 5}
        return legacy.get(v, 0)

    class Config:
        from_attributes = True


class AuditLogRead(BaseModel):
    id: int
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    target_code: Optional[str] = None  # 设备编码等，当 target_type=device 时由后端填充
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

