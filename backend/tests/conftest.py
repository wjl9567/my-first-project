"""
测试夹具：应用实例、HTTP 客户端、管理员/普通用户 Token、测试用设备与登记数据。
使用真实数据库，测试后清理创建的设备与登记记录；需在 .env 中配置 ADMIN_USERNAME / ADMIN_PASSWORD 用于登录。
"""
import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# 确保能导入 backend（项目根或 backend 上一级在 PYTHONPATH）
from backend.database import SessionLocal, get_db
from backend.main import create_app

# 测试用设备编号前缀，便于清理
TEST_DEVICE_CODE_PREFIX = "TEST_"


def _get_app():
    app = create_app()
    return app


@pytest.fixture(scope="session")
def app():
    return _get_app()


@pytest.fixture(scope="session")
def client(app) -> TestClient:
    return TestClient(app=app, base_url="http://test")


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """每个测试一个独立 DB 会话，用后关闭。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _login(client: TestClient, username: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, (r.status_code, r.text)
    data = r.json()
    return data["access_token"]


@pytest.fixture(scope="session")
def admin_token(client: TestClient) -> str:
    """管理员 Token（需 .env 中 ADMIN_USERNAME / ADMIN_PASSWORD）。"""
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    return _login(client, username, password)


@pytest.fixture(scope="session")
def admin_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def created_device_code(admin_headers: dict, client: TestClient) -> Generator[str, None, None]:
    """创建一台测试设备，yield device_code，测试后删除设备及关联登记。"""
    from backend import models

    code = f"{TEST_DEVICE_CODE_PREFIX}DEV_{id(object())}"
    r = client.post(
        "/api/devices",
        headers=admin_headers,
        json={
            "device_code": code,
            "name": "测试设备",
            "dept": "测试科",
            "status": 1,
        },
    )
    assert r.status_code in (200, 201), (r.status_code, r.text)
    yield code
    # 清理：删除该设备及该设备上的使用记录
    sess = SessionLocal()
    try:
        device = sess.query(models.Device).filter(models.Device.device_code == code).first()
        if device:
            sess.query(models.UsageRecord).filter(models.UsageRecord.device_code == code).delete()
            sess.delete(device)
            sess.commit()
    finally:
        sess.close()
