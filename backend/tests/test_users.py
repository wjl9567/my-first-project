"""用户列表接口：需登录、返回格式。"""
import pytest
from fastapi.testclient import TestClient


def test_users_list_requires_auth(client: TestClient):
    """用户列表需管理员，无 Token 应 401。"""
    r = client.get("/api/users")
    assert r.status_code == 401


def test_users_list_admin_success(client: TestClient, admin_headers: dict):
    """管理员获取用户列表应返回数组。"""
    r = client.get("/api/users", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_users_count(client: TestClient, admin_headers: dict):
    """用户总数。"""
    r = client.get("/api/users/count", headers=admin_headers)
    assert r.status_code == 200
    assert "total" in r.json()
