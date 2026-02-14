"""用户列表接口：需登录、返回格式。"""
import uuid

import pytest
from fastapi.testclient import TestClient


def test_users_list_requires_auth(client: TestClient):
    """用户列表需管理员，无 Token 应 401。"""
    r = client.get("/api/users")
    assert r.status_code == 401


def test_users_list_admin_success(client: TestClient, admin_headers: dict):
    """管理员获取用户列表应返回数组。"""
    r = client.get("/api/users", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_users_count(client: TestClient, admin_headers: dict):
    """用户总数。"""
    r = client.get("/api/users/count", headers=admin_headers)
    assert r.status_code == 200
    assert "total" in r.json()


def test_admin_update_user_password(client: TestClient, admin_headers: dict, db):
    """系统管理员可重置本地账号密码，重置后可用新密码登录。"""
    from backend import models
    from backend.auth import hash_password

    username = f"test_pw_{uuid.uuid4().hex[:12]}"
    u = models.User(
        wx_userid=None,
        username=username,
        real_name="测试用户",
        role="device_admin",
        dept=None,
        password_hash=hash_password("oldpass123"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    try:
        r = client.patch(f"/api/users/{u.id}/password", headers=admin_headers, json={"password": "newpass123"})
        assert r.status_code == 200, (r.status_code, r.text)
        assert r.json().get("ok") is True

        r_old = client.post("/api/auth/login", json={"username": username, "password": "oldpass123"})
        assert r_old.status_code == 401

        r_new = client.post("/api/auth/login", json={"username": username, "password": "newpass123"})
        assert r_new.status_code == 200
    finally:
        # 清理
        db.query(models.AuditLog).filter(models.AuditLog.actor_id == u.id).delete()
        db.delete(u)
        db.commit()


def test_admin_disable_enable_user(client: TestClient, admin_headers: dict, db):
    """系统管理员可停用/启用普通用户；停用后不可登录，启用后恢复。"""
    from backend import models
    from backend.auth import hash_password

    username = f"test_disable_{uuid.uuid4().hex[:12]}"
    u = models.User(
        wx_userid=None,
        username=username,
        real_name="待停用用户",
        role="user",
        dept=None,
        password_hash=hash_password("pass1234"),
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    try:
        r_login = client.post("/api/auth/login", json={"username": username, "password": "pass1234"})
        assert r_login.status_code == 200

        r = client.patch(f"/api/users/{u.id}/active", headers=admin_headers, json={"is_active": False})
        assert r.status_code == 200, (r.status_code, r.text)
        assert r.json().get("is_active") is False

        r_login2 = client.post("/api/auth/login", json={"username": username, "password": "pass1234"})
        assert r_login2.status_code == 403

        r2 = client.patch(f"/api/users/{u.id}/active", headers=admin_headers, json={"is_active": True})
        assert r2.status_code == 200
        assert r2.json().get("is_active") is True

        r_login3 = client.post("/api/auth/login", json={"username": username, "password": "pass1234"})
        assert r_login3.status_code == 200
    finally:
        db.query(models.AuditLog).filter(models.AuditLog.actor_id == u.id).delete()
        db.delete(u)
        db.commit()


def test_admin_cannot_disable_admin_accounts(client: TestClient, admin_headers: dict, db):
    """管理员账号（device_admin/sys_admin）不可被停用。"""
    from backend import models
    from backend.auth import hash_password

    username = f"test_admin_{uuid.uuid4().hex[:12]}"
    u = models.User(
        wx_userid=None,
        username=username,
        real_name="管理员用户",
        role="device_admin",
        dept=None,
        password_hash=hash_password("pass1234"),
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    try:
        r = client.patch(f"/api/users/{u.id}/active", headers=admin_headers, json={"is_active": False})
        assert r.status_code == 400
    finally:
        db.query(models.AuditLog).filter(models.AuditLog.actor_id == u.id).delete()
        db.delete(u)
        db.commit()


def test_admin_cannot_disable_self(client: TestClient, admin_headers: dict):
    """系统管理员不可停用自己。"""
    me = client.get("/api/auth/me", headers=admin_headers).json()
    r = client.patch(f"/api/users/{me['id']}/active", headers=admin_headers, json={"is_active": False})
    assert r.status_code == 400


def test_create_user_requires_auth(client: TestClient):
    """新增用户需管理员登录。"""
    r = client.post(
        "/api/users",
        json={"username": "newu", "password": "pass1234", "real_name": "新用户", "role": "user"},
    )
    assert r.status_code == 401


def test_create_user_success(client: TestClient, admin_headers: dict, db):
    """系统管理员可新增本地用户，创建后可用新账号登录。"""
    from backend import models

    username = f"test_new_{uuid.uuid4().hex[:12]}"
    r = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "username": username,
            "password": "pass1234",
            "real_name": "新测试用户",
            "role": "user",
            "dept": "测试科",
        },
    )
    assert r.status_code == 201, (r.status_code, r.text)
    data = r.json()
    assert data.get("username") == username
    assert data.get("real_name") == "新测试用户"
    assert data.get("role") == "user"
    assert data.get("dept") == "测试科"
    assert data.get("is_active") is True
    r_login = client.post("/api/auth/login", json={"username": username, "password": "pass1234"})
    assert r_login.status_code == 200
    # 清理（登录会写入审计，需先删审计再删用户）
    u = db.query(models.User).filter(models.User.username == username).first()
    if u:
        db.query(models.AuditLog).filter(models.AuditLog.actor_id == u.id).delete()
        db.delete(u)
        db.commit()


def test_create_user_duplicate_username_400(client: TestClient, admin_headers: dict, db):
    """用户名已存在时返回 400。"""
    from backend import models
    from backend.auth import hash_password

    username = f"test_dup_{uuid.uuid4().hex[:12]}"
    u = models.User(
        wx_userid=None,
        username=username,
        real_name="已有用户",
        role="user",
        password_hash=hash_password("pass1234"),
    )
    db.add(u)
    db.commit()
    try:
        r = client.post(
            "/api/users",
            headers=admin_headers,
            json={"username": username, "password": "pass1234", "real_name": "重复", "role": "user"},
        )
        assert r.status_code == 400
        assert "已存在" in (r.json().get("detail") or "")
    finally:
        db.delete(u)
        db.commit()


def test_device_admin_cannot_create_admin_role(client: TestClient, db):
    """设备管理员仅可创建普通用户，创建 device_admin/sys_admin 时返回 403。"""
    from backend import models
    from backend.auth import hash_password

    username = f"test_da_{uuid.uuid4().hex[:12]}"
    u = models.User(
        wx_userid=None,
        username=username,
        real_name="设备管理员",
        role="device_admin",
        password_hash=hash_password("pass1234"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    try:
        r_login = client.post("/api/auth/login", json={"username": username, "password": "pass1234"})
        assert r_login.status_code == 200
        token = r_login.json().get("access_token")
        headers = {"Authorization": "Bearer " + token} if token else {}
        r = client.post(
            "/api/users",
            headers=headers,
            json={"username": "newadmin", "password": "pass1234", "real_name": "新管", "role": "sys_admin"},
        )
        assert r.status_code == 403
        assert "仅可创建普通用户" in (r.json().get("detail") or "")
    finally:
        db.query(models.AuditLog).filter(models.AuditLog.actor_id == u.id).delete()
        db.delete(u)
        db.commit()
