"""企业微信 JS-SDK 签名接口：前端调用 wx.config 时需要的签名参数。"""
import hashlib
import time
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, status

from .auth import get_wecom_access_token
from .config import settings

router = APIRouter(prefix="/api/wecom", tags=["wecom"])

WECOM_GET_JSAPI_TICKET = "https://qyapi.weixin.qq.com/cgi-bin/get_jsapi_ticket"

_jsapi_ticket: Optional[str] = None
_jsapi_ticket_expires: float = 0


def _get_jsapi_ticket() -> str:
    global _jsapi_ticket, _jsapi_ticket_expires
    if _jsapi_ticket and time.time() < _jsapi_ticket_expires:
        return _jsapi_ticket
    access_token = get_wecom_access_token()
    timeout = getattr(settings, "WECOM_HTTP_TIMEOUT", 10.0)
    with httpx.Client(timeout=timeout) as client:
        r = client.get(
            WECOM_GET_JSAPI_TICKET,
            params={"access_token": access_token},
        )
    data = r.json()
    if data.get("errcode") != 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"获取 jsapi_ticket 失败: {data.get('errmsg', '')}",
        )
    _jsapi_ticket = data["ticket"]
    _jsapi_ticket_expires = time.time() + data.get("expires_in", 7200) - 60
    return _jsapi_ticket


def _sign(ticket: str, noncestr: str, timestamp: int, url: str) -> str:
    raw = f"jsapi_ticket={ticket}&noncestr={noncestr}&timestamp={timestamp}&url={url}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


@router.get("/js-sdk-config")
def get_js_sdk_config(
    url: str = Query(..., description="当前页面完整 URL（含 # 之前部分）"),
):
    """返回前端 wx.config 所需的签名参数。"""
    if not settings.WECOM_CORP_ID or not settings.WECOM_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="未配置企业微信",
        )
    ticket = _get_jsapi_ticket()
    import secrets
    noncestr = secrets.token_hex(8)
    timestamp = int(time.time())
    signature = _sign(ticket, noncestr, timestamp, url)
    return {
        "appId": settings.WECOM_CORP_ID,
        "timestamp": timestamp,
        "nonceStr": noncestr,
        "signature": signature,
    }
