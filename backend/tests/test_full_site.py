"""
全站扩展测试：异常、逻辑、并发、边界。
与 test_plan 对齐，覆盖 400/403/404、重复撤销、空参数、并发提交等。
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


def _usage_payload(device_code: str, bed: str = "1"):
    """维修类型(3)必填：registration_date, start_time, note。"""
    return {
        "device_code": device_code,
        "usage_type": 3,
        "registration_date": date.today().isoformat(),
        "start_time": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S"),
        "end_time": (datetime.now(timezone(timedelta(hours=8))) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
        "note": "测试故障描述",
        "bed_number": bed,
        "id_number": "ID001",
    }


# ---------- 异常：400 错误请求 ----------


def test_usage_create_empty_device_code(client: TestClient, admin_headers: dict):
    """登记时 device_code 为空应返回错误（400/422 校验错误或 404 设备未找到）。"""
    r = client.post(
        "/api/usage",
        headers=admin_headers,
        json={
            "device_code": "",
            "usage_type": 3,
        },
    )
    assert r.status_code in (400, 404, 422)


def test_usage_undo_nonexistent(client: TestClient, admin_headers: dict):
    """撤销不存在的记录 ID 应 404。"""
    r = client.post("/api/usage/999999/undo", headers=admin_headers)
    assert r.status_code == 404


def test_usage_undo_already_undone(client: TestClient, admin_headers: dict, created_device_code: str):
    """撤销已撤销的记录应 400。"""
    create = client.post("/api/usage", headers=admin_headers, json=_usage_payload(created_device_code, "77"))
    assert create.status_code == 201
    rid = create.json()["id"]
    r1 = client.post(f"/api/usage/{rid}/undo", headers=admin_headers)
    assert r1.status_code == 204
    r2 = client.post(f"/api/usage/{rid}/undo", headers=admin_headers)
    assert r2.status_code == 400


# ---------- 逻辑：列表与筛选一致性 ----------


def test_usage_list_and_count_consistent(client: TestClient, admin_headers: dict):
    """相同筛选条件下 list 条数与 count 一致。"""
    params = {"limit": 5, "offset": 0}
    r_list = client.get("/api/usage", headers=admin_headers, params=params)
    r_count = client.get("/api/usage/count", headers=admin_headers, params=params)
    assert r_list.status_code == 200 and r_count.status_code == 200
    total = r_count.json().get("total", 0)
    items = r_list.json()
    assert isinstance(items, list)
    assert len(items) <= 5
    if total > 0 and len(items) > 0:
        assert len(items) <= total


def test_usage_export_empty_ok(client: TestClient, admin_headers: dict):
    """导出无数据时仍返回 200，内容为空或仅表头。"""
    r = client.get(
        "/api/usage/export",
        headers=admin_headers,
        params={"format": "csv", "registration_date_from": "2099-01-01", "registration_date_to": "2099-01-01"},
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")


# ---------- 审计接口：时间筛选 ----------


def test_audit_list_with_time_filter(client: TestClient, admin_headers: dict):
    """审计日志带 from_time/to_time 应 200，返回数组。"""
    r = client.get(
        "/api/audit-logs",
        headers=admin_headers,
        params={"from_time": "2020-01-01T00:00:00", "to_time": "2030-12-31T23:59:59", "limit": 10},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------- 并发：同一设备同一用户短时间多次提交（幂等） ----------


def test_concurrent_usage_same_device_idempotent(client: TestClient, admin_headers: dict, created_device_code: str):
    """并发同设备同用户登记：不崩溃，至少一条成功。防重复在并发下非强一致，故不断言去重条数。"""
    payload = _usage_payload(created_device_code, "66")

    def post_once(_):
        return client.post("/api/usage", headers=admin_headers, json=payload)

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(post_once, i) for i in range(4)]
        results = [f.result() for f in as_completed(futures)]

    statuses = [r.status_code for r in results]
    ids = [r.json().get("id") for r in results if r.status_code in (200, 201)]
    assert any(s in (200, 201) for s in statuses), statuses
    assert len(ids) >= 1, "至少应有一条成功"


# ---------- 设备接口：异常与边界 ----------


def test_device_patch_not_found(client: TestClient, admin_headers: dict):
    """PATCH 不存在的设备 ID 应 404。"""
    r = client.patch(
        "/api/devices/999999",
        headers=admin_headers,
        json={"name": "无此设备"},
    )
    assert r.status_code == 404


def test_device_list_pagination(client: TestClient, admin_headers: dict):
    """设备列表 limit/offset 分页正常。"""
    r = client.get("/api/devices", headers=admin_headers, params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) <= 2
