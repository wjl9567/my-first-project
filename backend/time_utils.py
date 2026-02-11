"""
统一使用中国时区（UTC+8）处理业务时间，避免与前端/用户预期不符。
- 写入 DB 的“当前时刻”使用“中国现在”对应的 UTC 存储。
- 前端传入的 naive 日期时间按中国时区解析为 UTC 后存储。
- API 返回的 datetime 序列化为带 Z 的 ISO，便于前端按本地正确显示。
"""
from datetime import date, datetime, timedelta, timezone

# 中国时区 UTC+8
CHINA_TZ = timezone(timedelta(hours=8))
UTC = timezone.utc


def now_utc() -> datetime:
    """当前 UTC 时刻（用于需要绝对时间的场景，如审计、防重复窗口）。"""
    return datetime.now(UTC)


def now_china_as_utc() -> datetime:
    """当前中国时刻，以 UTC 表示（用于默认 start_time、cutoff 等业务“此刻”）。返回 naive UTC 便于存 DB。"""
    return datetime.now(CHINA_TZ).astimezone(UTC).replace(tzinfo=None)


def china_today() -> date:
    """中国时区“今天”的日期（用于默认 registration_date 等）。"""
    return datetime.now(CHINA_TZ).date()


def parse_naive_as_china_then_utc(dt: datetime | None) -> datetime | None:
    """
    将前端传来的 naive datetime 视为中国本地时间，转为 naive UTC 用于存库。
    若 dt 已带 tzinfo 则先转 UTC 再去掉 tzinfo。
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt.replace(tzinfo=CHINA_TZ).astimezone(UTC).replace(tzinfo=None)


def ensure_utc_aware(dt: datetime | None) -> datetime | None:
    """将 DB 读出的 naive datetime（约定为 UTC）转为 timezone-aware UTC，便于 Pydantic 序列化带 Z。"""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(UTC)
    return dt.replace(tzinfo=UTC)


def datetime_to_iso_utc(dt: datetime | None) -> str | None:
    """序列化为带 Z 的 ISO 字符串，前端解析为 UTC 后按本地时区显示。"""
    if dt is None:
        return None
    aware = ensure_utc_aware(dt)
    return aware.isoformat().replace("+00:00", "Z")


def utc_naive_to_china_str(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """将 DB 中的 naive UTC 转为中国时区后格式化为字符串，用于导出/展示。"""
    if dt is None:
        return ""
    aware = ensure_utc_aware(dt)
    return aware.astimezone(CHINA_TZ).strftime(fmt)
