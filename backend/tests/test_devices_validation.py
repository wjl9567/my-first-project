"""设备接口：空值/非法值、必填项校验。"""
import pytest
from fastapi.testclient import TestClient


def test_device_create_empty_code(client: TestClient, admin_headers: dict):
    """设备编号为空应返回 400。"""
    r = client.post(
        "/api/devices",
        headers=admin_headers,
        json={"device_code": "", "name": "设备", "dept": "科", "status": 1},
    )
    assert r.status_code == 400
    assert "编号" in (r.json().get("detail") or "")


def test_device_create_empty_name(client: TestClient, admin_headers: dict):
    """设备名称为空应返回 400。"""
    r = client.post(
        "/api/devices",
        headers=admin_headers,
        json={"device_code": "UNIQ_X", "name": "", "dept": "科", "status": 1},
    )
    assert r.status_code == 400
    assert "名称" in (r.json().get("detail") or "")
