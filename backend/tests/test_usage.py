"""使用/维护登记：创建、列表、总数、撤销、导出；无效设备、重复提交、权限。"""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


def test_usage_create_requires_auth(client: TestClient, created_device_code: str):
    """登记需登录，无 Token 返回 401。"""
    r = client.post(
        "/api/usage",
        json={
            "device_code": created_device_code,
            "usage_type": 1,
            "bed_number": "1",
            "id_number": "ID001",
        },
    )
    assert r.status_code == 401


def test_usage_create_invalid_device(client: TestClient, admin_headers: dict):
    """不存在的设备编号应返回 404。"""
    r = client.post(
        "/api/usage",
        headers=admin_headers,
        json={
            "device_code": "NOT_EXIST_DEVICE_XYZ",
            "usage_type": 3,
            "bed_number": "1",
            "id_number": "ID001",
        },
    )
    assert r.status_code == 404


def test_usage_create_success(client: TestClient, admin_headers: dict, created_device_code: str):
    """管理员登录后登记应成功，返回 201 及记录。"""
    r = client.post(
        "/api/usage",
        headers=admin_headers,
        json={
            "device_code": created_device_code,
            "usage_type": 3,
            "bed_number": "1",
            "id_number": "ID001",
            "patient_name": "测试",
            "registration_date": date.today().isoformat(),
            "start_time": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S"),
            "end_time": (datetime.now(timezone(timedelta(hours=8))) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            "equipment_condition": "normal",
            "daily_maintenance": "clean",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data.get("device_code") == created_device_code
    assert data.get("bed_number") == "1"
    assert data.get("id_number") == "ID001"
    assert data.get("equipment_condition") == "normal"
    assert data.get("daily_maintenance") == "clean"


def test_usage_create_without_bed_id_optional(client: TestClient, admin_headers: dict, created_device_code: str):
    """床号、ID 号为选填：不传或传 null 时仍可提交成功，返回记录中为 null。"""
    r = client.post(
        "/api/usage",
        headers=admin_headers,
        json={
            "device_code": created_device_code,
            "usage_type": 3,
            "registration_date": date.today().isoformat(),
            "start_time": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S"),
            "end_time": (datetime.now(timezone(timedelta(hours=8))) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            "equipment_condition": "abnormal",
            "daily_maintenance": "disinfect",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data.get("device_code") == created_device_code
    assert data.get("bed_number") is None or data.get("bed_number") == ""
    assert data.get("id_number") is None or data.get("id_number") == ""
    assert data.get("equipment_condition") == "abnormal"
    assert data.get("daily_maintenance") == "disinfect"


def test_usage_list_requires_auth(client: TestClient):
    """使用记录列表无 Token 应 401。"""
    r = client.get("/api/usage")
    assert r.status_code == 401


def test_usage_list_success(client: TestClient, admin_headers: dict):
    """带 Token 获取列表应返回 200 与数组。"""
    r = client.get("/api/usage", headers=admin_headers, params={"limit": 10})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_usage_count_requires_auth(client: TestClient):
    """使用记录总数无 Token 应 401。"""
    r = client.get("/api/usage/count")
    assert r.status_code == 401


def test_usage_count_success(client: TestClient, admin_headers: dict):
    """带 Token 获取总数应返回 total。"""
    r = client.get("/api/usage/count", headers=admin_headers)
    assert r.status_code == 200
    assert "total" in r.json()


def test_usage_export_requires_admin(client: TestClient, admin_headers: dict):
    """导出接口需管理员；普通用户若为 user 角色则 403（本项目中 conftest 为 admin，这里仅验证无 Token 401）。"""
    r = client.get("/api/usage/export", params={"format": "csv"})
    assert r.status_code == 401


def test_usage_export_csv_success(client: TestClient, admin_headers: dict):
    """管理员导出 CSV 应返回 200。"""
    r = client.get("/api/usage/export", headers=admin_headers, params={"format": "csv"})
    assert r.status_code == 200
    assert "csv" in r.headers.get("content-type", "").lower()


def test_usage_undo_requires_auth(client: TestClient):
    """撤销登记无 Token 应 401。"""
    r = client.post("/api/usage/1/undo")
    assert r.status_code == 401


def test_usage_duplicate_submit_idempotent(client: TestClient, admin_headers: dict, created_device_code: str):
    """短时间同一用户、同一设备重复提交：应返回同一条记录（防重复）。"""
    payload = {
        "device_code": created_device_code,
        "usage_type": 3,
        "bed_number": "88",
        "id_number": "ID88",
    }
    r1 = client.post("/api/usage", headers=admin_headers, json=payload)
    r2 = client.post("/api/usage", headers=admin_headers, json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


def test_usage_list_filter_by_bed(client: TestClient, admin_headers: dict, created_device_code: str):
    """按床号筛选列表。"""
    # 先创建一条带床号的记录
    client.post(
        "/api/usage",
        headers=admin_headers,
        json={
            "device_code": created_device_code,
            "usage_type": 3,
            "bed_number": "99",
            "id_number": "ID99",
        },
    )
    r = client.get("/api/usage", headers=admin_headers, params={"bed_number": "99", "limit": 10})
    assert r.status_code == 200
    items = r.json()
    if items:
        assert any(u.get("bed_number") == "99" for u in items)
