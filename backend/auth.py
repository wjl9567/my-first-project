"""企业微信 OAuth、本地管理员密码登录与 JWT 鉴权。"""
import time
from typing import Optional

import httpx
import jwt
import bcrypt
from fastapi import Depends, HTTPException
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db

# 企业微信 API
WECOM_GET_TOKEN = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
WECOM_GET_USERINFO = "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo"
WECOM_OAUTH_AUTHORIZE = "https://open.weixin.qq.com/connect/oauth2/authorize"

# 内存缓存 access_token（生产建议用 Redis）
_wecom_token: Optional[str] = None
_wecom_token_expires: float = 0


def get_wecom_access_token() -> str:
    """获取企业微信应用 access_token（带简单缓存）。"""
    global _wecom_token, _wecom_token_expires
    if not settings.WECOM_CORP_ID or not settings.WECOM_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="未配置企业微信（WECOM_CORP_ID / WECOM_SECRET）",
        )
    if _wecom_token and time.time() < _wecom_token_expires:
        return _wecom_token
    timeout = getattr(settings, "WECOM_HTTP_TIMEOUT", 10.0)
    with httpx.Client(timeout=timeout) as client:
        r = client.get(
            WECOM_GET_TOKEN,
            params={
                "corpid": settings.WECOM_CORP_ID,
                "corpsecret": settings.WECOM_SECRET,
            },
        )
    data = r.json()
    if data.get("errcode") != 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"企业微信 gettoken 失败: {data.get('errmsg', '')}",
        )
    _wecom_token = data["access_token"]
    _wecom_token_expires = time.time() + data.get("expires_in", 7200) - 60
    return _wecom_token


def get_wecom_userid(code: str) -> str:
    """用 code 换取企业微信 userid（企业成员）。"""
    token = get_wecom_access_token()
    timeout = getattr(settings, "WECOM_HTTP_TIMEOUT", 10.0)
    with httpx.Client(timeout=timeout) as client:
        r = client.get(
            WECOM_GET_USERINFO,
            params={"access_token": token, "code": code},
        )
    data = r.json()
    if data.get("errcode") != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取用户身份失败: {data.get('errmsg', '')}",
        )
    userid = data.get("userid")
    if not userid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非企业成员或 code 无效",
        )
    return userid


# bcrypt 只接受最多 72 字节，直接用 bcrypt 库并截断，避免 passlib 内部仍收到超长密码
_BCRYPT_MAX_BYTES = 72


def _password_bytes(plain: str) -> bytes:
    """密码转为最多 72 字节的 bytes，避免 bcrypt 报错。"""
    raw = (plain or "").encode("utf-8")
    return raw[:_BCRYPT_MAX_BYTES]


def truncate_password_for_bcrypt(plain: str) -> str:
    """将密码截断为最多 72 字节（用于登录比较等）。"""
    return _password_bytes(plain).decode("utf-8", errors="ignore")


def hash_password(plain: str) -> str:
    """密码哈希，用于存储。直接使用 bcrypt，传入前截断到 72 字节。"""
    pw = _password_bytes(plain)
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希。直接使用 bcrypt，传入前截断到 72 字节。"""
    if not hashed:
        return False
    pw = _password_bytes(plain)
    hashed_b = hashed.encode("utf-8") if isinstance(hashed, str) else hashed
    return bcrypt.checkpw(pw, hashed_b)


def create_access_token(user: models.User) -> str:
    """生成 JWT，payload 含 id, wx_userid, role。"""
    expire = int(time.time()) + settings.JWT_EXPIRE_HOURS * 3600
    payload = {
        "sub": str(user.id),
        "wx_userid": user.wx_userid if user.wx_userid else "",
        "role": user.role,
        "exp": expire,
        "iat": int(time.time()),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> Optional[dict]:
    """解析 JWT，失败返回 None。"""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except Exception:
        return None


security = HTTPBearer(auto_error=False)


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[models.User]:
    """依赖：当前用户（可选）。无 token 或无效时返回 None。"""
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        return None
    user_id = int(payload["sub"])
    user = db.get(models.User, user_id)
    if not user:
        return None
    # 停用账号：明确提示（而不是当成未登录）
    if getattr(user, "is_active", True) is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已停用，请联系管理员",
        )
    return user


def get_current_user(
    user: Optional[models.User] = Depends(get_current_user_optional),
) -> models.User:
    """依赖：当前用户（必选）。未登录则 401。"""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )
    return user


def require_role(*allowed_roles: str):
    """依赖：要求当前用户角色在 allowed_roles 内。"""
    def _require(current_user: models.User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足",
            )
        return current_user
    return _require
