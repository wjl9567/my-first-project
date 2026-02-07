"""院内访问控制：对 /admin、/docs、管理员登录接口校验来源（Origin/Referer 或 IP 白名单）。"""
import ipaddress
import logging
from typing import List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import get_allowed_admin_origins, get_allowed_admin_ips, settings

logger = logging.getLogger(__name__)

# 需要院内校验的路径前缀（仅对这些路径做校验；配置为空时不拦截任何请求）
_ADMIN_PATH_PREFIXES = ("/admin", "/docs", "/api/auth/login")


def _client_ip(request: Request) -> str:
    """优先从 X-Forwarded-For 取第一个（客户端 IP），否则 request.client.host。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def _origin_or_referer(request: Request) -> str:
    """返回 Origin 或 Referer（用于与白名单比对）。"""
    origin = request.headers.get("origin") or ""
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer") or ""
    if referer:
        try:
            # 取 scheme + host，去掉 path
            from urllib.parse import urlparse
            p = urlparse(referer)
            return f"{p.scheme}://{p.netloc}" if p.netloc else ""
        except Exception:
            pass
    return ""


def _ip_in_allowed(client_ip_str: str, allowed: List[str]) -> bool:
    """判断 client_ip_str 是否在 allowed（IP 或 CIDR）列表中。"""
    if not client_ip_str or not allowed:
        return False
    try:
        ip = ipaddress.ip_address(client_ip_str)
    except ValueError:
        return False
    for item in allowed:
        item = item.strip()
        if not item:
            continue
        if "/" in item:
            try:
                net = ipaddress.ip_network(item, strict=False)
                if ip in net:
                    return True
            except ValueError:
                continue
        else:
            try:
                if ip == ipaddress.ip_address(item):
                    return True
            except ValueError:
                continue
    return False


def _origin_matches_allowed(origin: str, allowed: List[str]) -> bool:
    """判断 origin 是否以任一 allowed 前缀开头（允许子路径）。"""
    if not origin or not allowed:
        return False
    origin_lower = origin.lower().rstrip("/")
    for prefix in allowed:
        prefix_lower = prefix.lower().rstrip("/")
        if origin_lower == prefix_lower or origin_lower.startswith(prefix_lower + "/"):
            return True
    return False


def is_admin_path(request: Request) -> bool:
    """请求路径是否需要院内访问校验。POST /api/auth/login 需校验，其它为 /admin、/docs。"""
    path = (request.url.path or "").split("?")[0]
    if path == "/api/auth/login" or path.startswith("/api/auth/login/"):
        return request.method.upper() == "POST"
    return path == "/admin" or path.startswith("/admin/") or path == "/docs" or path.startswith("/docs/")


def allow_admin_access(request: Request) -> bool:
    """
    判断当前请求是否允许访问受保护的管理端资源。
    当 ALLOWED_ADMIN_ORIGINS 与 ALLOWED_ADMIN_IPS 均为空时，不校验（允许所有，便于开发）。
    """
    origins = get_allowed_admin_origins()
    ips = get_allowed_admin_ips()
    if not origins and not ips:
        return True

    origin_val = _origin_or_referer(request)
    client_ip_val = _client_ip(request)

    if origins and _origin_matches_allowed(origin_val, origins):
        return True
    if ips and _ip_in_allowed(client_ip_val, ips):
        return True

    logger.warning("admin_access_denied path=%s origin=%s client_ip=%s", request.url.path, origin_val, client_ip_val)
    return False


class AdminAccessMiddleware(BaseHTTPMiddleware):
    """对 /admin、/docs、POST /api/auth/login 校验院内来源，非法来源返回 403。"""

    async def dispatch(self, request: Request, call_next):
        if not is_admin_path(request):
            return await call_next(request)
        if allow_admin_access(request):
            return await call_next(request)
        return JSONResponse(
            status_code=403,
            content={"detail": "仅允许院内网络或指定来源访问后台与文档"},
        )
