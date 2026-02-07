"""应用配置：企业微信、JWT、院内访问控制等（从环境变量读取）。"""
import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv

load_dotenv()

# 生产环境若未设置 JWT_SECRET 或仍为默认值，启动时应拒绝（在 main 中校验）
JWT_SECRET_DEFAULT = "change-me-in-production"


@lru_cache
def get_settings():
    class Settings:
        # 数据库
        DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://user:password@localhost:5432/device_scan",
        )
        # 企业微信（未配置时登录接口会返回 503，H5 仍可用无登录模式）
        WECOM_CORP_ID: str = os.getenv("WECOM_CORP_ID", "")
        WECOM_AGENT_ID: str = os.getenv("WECOM_AGENT_ID", "")
        WECOM_SECRET: str = os.getenv("WECOM_SECRET", "")
        # 回调与前端 base（用于拼 redirect_uri 和登录后跳转）
        BASE_URL: str = os.getenv("BASE_URL", "http://127.0.0.1:8000")
        # JWT（生产环境必须设置环境变量覆盖默认值）
        JWT_SECRET: str = os.getenv("JWT_SECRET", JWT_SECRET_DEFAULT)
        JWT_ALGORITHM: str = "HS256"
        JWT_EXPIRE_HOURS: int = 24
        # 本地管理员（可选）：首次用该账号密码登录时会自动创建 sys_admin 用户）
        ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "")
        ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
        # 院内访问控制：后台 /admin、/docs 仅允许以下来源访问（为空则不校验，便于开发）
        # ALLOWED_ADMIN_ORIGINS: 逗号分隔的 Origin 前缀，如 https://admin.xxx.edu.cn,https://192.168.1.1
        # ALLOWED_ADMIN_IPS: 逗号分隔的 IP 或 CIDR，如 192.168.0.0/16,10.0.0.1
        ALLOWED_ADMIN_ORIGINS: str = os.getenv("ALLOWED_ADMIN_ORIGINS", "")
        ALLOWED_ADMIN_IPS: str = os.getenv("ALLOWED_ADMIN_IPS", "")
        # 企业微信 HTTP 请求超时（秒）
        WECOM_HTTP_TIMEOUT: float = float(os.getenv("WECOM_HTTP_TIMEOUT", "10.0"))
    return Settings()


settings = get_settings()


def get_allowed_admin_origins() -> List[str]:
    """解析允许的 Origin 列表，用于院内访问校验。"""
    raw = (settings.ALLOWED_ADMIN_ORIGINS or "").strip()
    if not raw:
        return []
    return [s.strip().rstrip("/") for s in raw.split(",") if s.strip()]


def get_allowed_admin_ips() -> List[str]:
    """解析允许的 IP/CIDR 列表，用于院内访问校验。"""
    raw = (settings.ALLOWED_ADMIN_IPS or "").strip()
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]
