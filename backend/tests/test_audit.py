"""审计日志接口：需管理员、返回列表。"""
import pytest
from fastapi.testclient import TestClient


def test_audit_list_requires_auth(client: TestClient):
    """审计列表无 Token 应 401。"""
    r = client.get("/api/audit-logs")
    assert r.status_code == 401


def test_audit_list_admin_success(client: TestClient, admin_headers: dict):
    """管理员获取审计列表应返回数组。"""
    r = client.get("/api/audit-logs", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
