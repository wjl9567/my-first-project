"""企业微信 OAuth 与本地管理员账号密码登录。"""
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import models
from .audit import log_audit
from .auth import (
    create_access_token,
    get_wecom_userid,
    get_current_user,
    verify_password,
    hash_password,
    truncate_password_for_bcrypt,
)
from .config import settings
from .database import get_db
from .schemas import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 企业微信网页授权链接（文档 91022）
WECOM_OAUTH_AUTHORIZE = "https://open.weixin.qq.com/connect/oauth2/authorize"


@router.get("/wecom/login")
def wecom_login(
    request: Request,
    next_path: str = "/h5/scan",  # 登录成功后跳转的路径
):
    """
    重定向到企业微信授权页。企业微信授权后会带着 code 回调到 /api/auth/wecom/callback。
    """
    if not settings.WECOM_CORP_ID or not settings.WECOM_AGENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="未配置企业微信（WECOM_CORP_ID / WECOM_AGENT_ID）",
        )
    redirect_uri = f"{settings.BASE_URL.rstrip('/')}/api/auth/wecom/callback"
    state = quote(next_path)
    params = {
        "appid": settings.WECOM_CORP_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "snsapi_base",
        "state": state,
        "agentid": settings.WECOM_AGENT_ID,
    }
    url = f"{WECOM_OAUTH_AUTHORIZE}?{urlencode(params)}#wechat_redirect"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url, status_code=302)


@router.get("/wecom/callback")
def wecom_callback(
    request: Request,
    code: str = "",
    state: str = "/h5/scan",
    db: Session = Depends(get_db),
):
    """
    企业微信回调：用 code 换 userid，创建或更新本系统用户，签发 JWT，重定向到 H5 并带上 token。
    """
    if not code:
        raise HTTPException(status_code=400, detail="缺少 code")
    userid = get_wecom_userid(code)
    user = db.query(models.User).filter(models.User.wx_userid == userid).first()
    if not user:
        user = models.User(
            wx_userid=userid,
            real_name=userid,  # 可后续用通讯录接口拉取姓名
            role="user",
        )
        db.add(user)
        db.flush()
        log_audit(db, user.id, "auth.login", "user", user.id, "wecom", do_commit=False)
        db.commit()
        db.refresh(user)
    else:
        if getattr(user, "is_active", True) is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用，请联系管理员")
        log_audit(db, user.id, "auth.login", "user", user.id, "wecom")
    token = create_access_token(user)
    # 开放重定向防护：仅允许以单斜杠开头的相对路径，且不含 //
    next_path = (state or "").strip() or "/h5/scan"
    if not next_path.startswith("/") or "//" in next_path:
        next_path = "/h5/scan"
    if "?" in next_path:
        target = f"{settings.BASE_URL.rstrip('/')}{next_path}&token={token}"
    else:
        target = f"{settings.BASE_URL.rstrip('/')}{next_path}#token={token}"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=target, status_code=302)


@router.post("/login")
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    管理员账号密码登录。成功后返回 access_token，前端存到 localStorage 并带 Authorization: Bearer <token> 请求。
    若配置了 ADMIN_USERNAME / ADMIN_PASSWORD，首次用该账号密码登录时会自动创建 sys_admin 用户。
    """
    username = (payload.username or "").strip()
    # 先截断到 72 字节，避免 bcrypt 报错
    password = truncate_password_for_bcrypt(payload.password or "")
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入用户名")
    if not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入密码")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        # 允许用环境变量中的管理员账号首次登录并创建用户（比较时用截断后的密码）
        admin_pwd = truncate_password_for_bcrypt(settings.ADMIN_PASSWORD or "")
        if (
            settings.ADMIN_USERNAME
            and settings.ADMIN_PASSWORD
            and username == settings.ADMIN_USERNAME
            and password == admin_pwd
        ):
            user = models.User(
                wx_userid=None,
                username=username,
                real_name=username,
                role="sys_admin",
                password_hash=hash_password(password),
            )
            db.add(user)
            db.flush()
            log_audit(db, user.id, "auth.login", "user", user.id, "password", do_commit=False)
            db.commit()
            db.refresh(user)
            token = create_access_token(user)
            return {"access_token": token, "token_type": "bearer"}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    else:
        if getattr(user, "is_active", True) is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用，请联系管理员")
        if not user.password_hash:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="该账号未设置密码，请使用企业微信登录")
        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token(user)
    log_audit(db, user.id, "auth.login", "user", user.id, "password")
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def auth_me(current_user: models.User = Depends(get_current_user)):
    """返回当前登录用户信息（需 Bearer token）。"""
    return {
        "id": current_user.id,
        "wx_userid": current_user.wx_userid,
        "real_name": current_user.real_name,
        "role": current_user.role,
        "dept": current_user.dept,
    }
