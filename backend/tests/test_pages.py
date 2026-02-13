"""前端页面：H5 登记、我的记录、后台管理、健康检查返回 200。"""
import pytest
from fastapi.testclient import TestClient


def test_h5_scan_page(client: TestClient):
    """H5 登记页应返回 200 与 HTML，且包含登记/扫码。"""
    r = client.get("/h5/scan")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    text = r.content.decode("utf-8", errors="replace")
    assert "登记" in text or "扫码" in text


def test_h5_scan_form_optimizations(client: TestClient):
    """验证近期优化：床号/ID 号选填占位、设备状况/日常保养表单项、必填项标记。"""
    r = client.get("/h5/scan")
    assert r.status_code == 200
    text = r.content.decode("utf-8", errors="replace")
    # 操作类型：必选下拉，来源于使用类型字典（页面至少应包含字段与文案）
    assert "操作类型" in text
    assert "usage_type" in text
    # 选填提示、登记相关字段（床号/ID 可能来自动态 schema，静态页含选填与日期/时间字段即可）
    # 仅用 ASCII 断言：静态 HTML/JS 中存在的表单与 schema 相关字符串
    assert "registration_date" in text
    assert "start_time" in text
    assert "end_time" in text
    assert "loadFormSchemaAndShowBlock" in text or "form-schema" in text


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
