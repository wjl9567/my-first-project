"""前端页面：H5 登记、我的记录、后台管理、健康检查返回 200。"""
import pytest
from fastapi.testclient import TestClient


def test_h5_scan_page(client: TestClient):
    """H5 登记页应返回 200 与 HTML。"""
    r = client.get("/h5/scan")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    text = r.content.decode("utf-8", errors="replace")
    assert "登记" in text or "扫码" in text


def test_h5_my_records_page(client: TestClient):
    """H5 我的记录页应返回 200 与 HTML。"""
    r = client.get("/h5/my-records")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_admin_page(client: TestClient):
    """后台管理页应返回 200 与 HTML。"""
    r = client.get("/admin")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
