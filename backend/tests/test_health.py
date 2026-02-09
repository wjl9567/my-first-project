"""健康检查与根路径接口测试。"""
import pytest
from fastapi.testclient import TestClient


def test_health(client: TestClient):
    """GET /health 返回 200 与 status ok。"""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_root(client: TestClient):
    """GET / 返回 API 在线说明。"""
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert "API" in data["message"] or "在线" in data["message"]
