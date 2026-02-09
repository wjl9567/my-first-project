"""字典接口：使用类型/设备状态列表、增删改需权限。"""
import pytest
from fastapi.testclient import TestClient


def test_dict_list_usage_type(client: TestClient, admin_headers: dict):
    """获取使用类型字典应返回数组。"""
    r = client.get("/api/dict", params={"dict_type": "usage_type"}, headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_dict_list_device_status(client: TestClient, admin_headers: dict):
    """获取设备状态字典应返回数组。"""
    r = client.get("/api/dict", params={"dict_type": "device_status"}, headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_dict_create_requires_auth(client: TestClient):
    """新增字典项无 Token 应 401。"""
    r = client.post(
        "/api/dict",
        json={"dict_type": "usage_type", "code": 99, "label": "测试项"},
    )
    assert r.status_code == 401
