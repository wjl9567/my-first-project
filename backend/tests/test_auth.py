"""认证接口：管理员登录、/me、空/非法参数、错误密码。"""
import pytest
from fastapi.testclient import TestClient


def test_login_success(client: TestClient, admin_headers: dict):
    """正确用户名密码登录应返回 200 与 access_token。"""
    # 使用与 conftest 相同的账号（conftest 已登录过，这里再登一次验证接口）
    import os
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    data = r.json()
    assert data.get("token_type") == "bearer"
    assert "access_token" in data and len(data["access_token"]) > 0


def test_login_empty_username(client: TestClient):
    """用户名为空应返回 400。"""
    r = client.post("/api/auth/login", json={"username": "", "password": "x"})
    assert r.status_code == 400
    assert "用户名" in (r.json().get("detail") or "")


def test_login_empty_password(client: TestClient):
    """密码为空应返回 400。"""
    r = client.post("/api/auth/login", json={"username": "admin", "password": ""})
    assert r.status_code == 400
    assert "密码" in (r.json().get("detail") or "")


def test_login_wrong_password(client: TestClient):
    """错误密码应返回 401。"""
    import os
    username = os.getenv("ADMIN_USERNAME", "admin")
    r = client.post("/api/auth/login", json={"username": username, "password": "wrongpassword"})
    assert r.status_code == 401


def test_me_requires_auth(client: TestClient):
    """GET /api/auth/me 无 Token 应返回 401。"""
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_success(client: TestClient, admin_headers: dict):
    """GET /api/auth/me 带有效 Token 应返回当前用户信息。"""
    r = client.get("/api/auth/me", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert "role" in data
    assert data["role"] in ("sys_admin", "device_admin", "user")


def test_wecom_login_when_not_configured(client: TestClient):
    """未配置企业微信时 GET /api/auth/wecom/login 应返回 503 且为友好 HTML（避免 JSON 乱码）。"""
    r = client.get("/api/auth/wecom/login", params={"next_path": "/h5/my-records"})
    if r.status_code == 503:
        ct = r.headers.get("content-type", "")
        assert "text/html" in ct
        assert "utf-8" in ct.lower() or "charset" in ct.lower()
        text = r.content.decode("utf-8", errors="replace")
        assert "未配置企业微信" in text
        assert "WECOM_CORP_ID" in text or "企业微信" in text
        assert "/h5/scan" in text or "设备" in text
    else:
        assert r.status_code == 302, "若已配置企微则应为重定向"
