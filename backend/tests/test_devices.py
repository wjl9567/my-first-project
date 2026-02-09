"""设备模块：增删改查、列表筛选、联想、导出、二维码、权限与异常。"""
import pytest
from fastapi.testclient import TestClient


def test_device_create_requires_admin(client: TestClient):
    """创建设备需管理员，无 Token 返回 401。"""
    r = client.post(
        "/api/devices",
        json={"device_code": "X001", "name": "设备", "dept": "科", "status": 1},
    )
    assert r.status_code == 401


def test_device_create_success(client: TestClient, admin_headers: dict, created_device_code: str):
    """管理员创建设备应成功，返回 201 及设备信息。"""
    assert created_device_code.startswith("TEST_")
    r = client.get("/api/devices", headers=admin_headers, params={"q": created_device_code})
    assert r.status_code == 200
    items = r.json()
    assert any(d["device_code"] == created_device_code for d in items)


def test_device_create_duplicate_code(client: TestClient, admin_headers: dict, created_device_code: str):
    """重复设备编号应返回 400。"""
    r = client.post(
        "/api/devices",
        headers=admin_headers,
        json={
            "device_code": created_device_code,
            "name": "另一台",
            "dept": "科",
            "status": 1,
        },
    )
    assert r.status_code == 400
    assert "已存在" in (r.json().get("detail") or "")


def test_device_list_optional_auth(client: TestClient, admin_headers: dict):
    """设备列表可无 Token 或带 Token 访问（设计允许）。"""
    r = client.get("/api/devices")
    assert r.status_code == 200
    r2 = client.get("/api/devices", headers=admin_headers)
    assert r2.status_code == 200


def test_device_suggest(client: TestClient, admin_headers: dict, created_device_code: str):
    """联想接口返回含设备编号/名称的列表。"""
    r = client.get("/api/devices/suggest", headers=admin_headers, params={"q": "测试", "limit": 10})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        assert "device_code" in data[0] and "name" in data[0]


def test_device_get_by_id(client: TestClient, admin_headers: dict, created_device_code: str):
    """根据 ID 获取单台设备。"""
    list_r = client.get("/api/devices", headers=admin_headers, params={"q": created_device_code})
    assert list_r.status_code == 200
    items = list_r.json()
    dev = next((d for d in items if d["device_code"] == created_device_code), None)
    if not dev:
        pytest.skip("created_device_code 未在列表中")
    r = client.get(f"/api/devices/{dev['id']}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["device_code"] == created_device_code


def test_device_get_not_found(client: TestClient, admin_headers: dict):
    """不存在的设备 ID 返回 404。"""
    r = client.get("/api/devices/999999", headers=admin_headers)
    assert r.status_code == 404


def test_device_patch_requires_admin(client: TestClient, admin_headers: dict, created_device_code: str):
    """更新设备需管理员。"""
    list_r = client.get("/api/devices", headers=admin_headers, params={"q": created_device_code})
    items = list_r.json()
    dev = next((d for d in items if d["device_code"] == created_device_code), None)
    if not dev:
        pytest.skip("no device")
    r = client.patch(
        f"/api/devices/{dev['id']}",
        json={"name": "新名称"},
    )
    assert r.status_code == 401


def test_device_count(client: TestClient, admin_headers: dict):
    """设备总数接口返回 total。"""
    r = client.get("/api/devices/count", headers=admin_headers)
    assert r.status_code == 200
    assert "total" in r.json()


def test_device_export_csv_requires_admin(client: TestClient):
    """设备导出无 Token 应 401。"""
    r = client.get("/api/devices/export?format=csv")
    assert r.status_code == 401


def test_device_export_csv_success(client: TestClient, admin_headers: dict):
    """管理员导出 CSV 应返回 200 与 csv 内容。"""
    r = client.get("/api/devices/export", headers=admin_headers, params={"format": "csv"})
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
