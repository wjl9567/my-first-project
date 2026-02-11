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
    # 床号、ID 号为选填：placeholder 或文案含「选填」
    assert "选填" in text
    assert "bed_number" in text or "床号" in text
    assert "id_number" in text or "ID" in text or "ID号" in text
    # 设备状况、日常保养（无红色必填 * 在标题上，表单项存在）
    assert "设备状况" in text
    assert "日常保养" in text
    # 登记日期、开机/关机时间等必填项有 required 或 label 结构
    assert "登记日期" in text
    assert "开机" in text or "start_time" in text
    assert "关机" in text or "end_time" in text
    # 单选值：normal/abnormal, clean/disinfect
    assert "normal" in text or "abnormal" in text
    assert "clean" in text or "disinfect" in text


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
