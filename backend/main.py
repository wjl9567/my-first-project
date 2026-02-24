import logging
import os
import pathlib

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import JWT_SECRET_DEFAULT, settings
from .database import Base, engine
from .device_code_utils import normalize_device_code
from . import models
from . import routes_auth, routes_audit, routes_dashboard, routes_devices, routes_dict, routes_usage, routes_users
from .admin_access import AdminAccessMiddleware

_logger = logging.getLogger(__name__)

_BASE = pathlib.Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(_BASE / "templates"))

_DOCS_TITLE = "医院设备扫码登记系统 - API 文档"
_DOCS_DESCRIPTION = (
    "用于院内设备使用登记、查询与导出。"
    "需权限的接口请先通过企业微信登录或携带管理员 token（Authorization: Bearer &lt;token&gt;）再调用。"
)


def create_app() -> FastAPI:
    # 创建所有表（MVP 阶段可直接使用，后续可改为 Alembic 迁移）
    Base.metadata.create_all(bind=engine)
    # 轻量自迁移：为 users 增加 is_active（停用/启用）（SQLite 不支持 ADD COLUMN IF NOT EXISTS，用 try 忽略已存在）
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                conn.commit()
            except Exception as e:
                if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                    raise
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_is_active ON users (is_active)"))
                conn.commit()
            except Exception:
                pass
    except Exception:
        _logger.exception("users.is_active 自动迁移失败（请检查数据库权限或手工执行迁移）")
    # 轻量自迁移：已有表缺列时自动 ADD COLUMN（部署到生产时无需手写 SQL）
    # 格式: (表名, 列名, 类型表达式)，列已存在则忽略
    _add_columns = [
        ("usage_records", "returned_at", "TIMESTAMP"),
        ("usage_records", "repair_completed_at", "TIMESTAMP"),
        ("usage_records", "registration_date", "DATE"),
        ("usage_records", "is_deleted", "BOOLEAN DEFAULT FALSE"),
        ("usage_records", "photo_urls", "TEXT"),
        ("usage_records", "terminal_disinfection", "TEXT"),
        ("devices", "is_deleted", "BOOLEAN DEFAULT FALSE"),
    ]
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            for table, col, type_sql in _add_columns:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {type_sql}"))
                    conn.commit()
                except Exception as e:
                    err = str(e).lower()
                    if "duplicate column" in err or "already exists" in err:
                        pass
                    else:
                        _logger.warning("自迁移 %s.%s 跳过: %s", table, col, e)
    except Exception:
        _logger.exception("轻量自迁移失败（请检查数据库权限或手工执行迁移）")
    # 字典表为空时写入初始数据
    from .database import SessionLocal
    try:
        db = SessionLocal()
        if db.query(models.DictItem).first() is None:
            for item in [
                ("usage_type", 1, "常规使用", 1),
                ("usage_type", 2, "借用", 2),
                ("usage_type", 3, "维修/故障", 3),
                ("usage_type", 4, "校准/质控", 4),
                ("usage_type", 5, "其他", 5),
                ("device_status", 1, "可用", 1),
                ("device_status", 2, "使用中", 2),
                ("device_status", 3, "维修中", 3),
                ("device_status", 4, "故障", 4),
                ("device_status", 5, "报废", 5),
            ]:
                db.add(models.DictItem(dict_type=item[0], code=str(item[1]), label=item[2], sort_order=item[3]))
            db.commit()
        db.close()
    except Exception:
        _logger.exception("字典种子数据写入失败")

    app = FastAPI(
        title=_DOCS_TITLE,
        description=_DOCS_DESCRIPTION,
        version="0.1.3",
        docs_url=None,
        redoc_url=None,
    )

    # 院内访问控制：对 /admin、/docs、POST /api/auth/login 校验 Origin 或 IP 白名单（配置为空则不校验）
    app.add_middleware(AdminAccessMiddleware)

    @app.on_event("startup")
    def _check_jwt_secret():
        if settings.JWT_SECRET == JWT_SECRET_DEFAULT:
            _logger.warning("JWT_SECRET 仍为默认值，生产环境请设置环境变量 JWT_SECRET")
            if os.getenv("ENVIRONMENT", "").lower() == "production":
                raise RuntimeError("生产环境必须设置 JWT_SECRET 环境变量，且不可使用默认值")

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    @app.get("/")
    async def root():
        return {"message": "设备扫码登记系统 API 在线"}

    # 短链：扫带「纯编号」的二维码时，若打印为 URL 可指向此路径，自动跳转登记页（支持现有资产码多行/一行内容，只取编码）
    @app.get("/s/{device_code}", response_class=RedirectResponse, include_in_schema=False)
    async def short_scan_redirect(device_code: str):
        code = normalize_device_code(device_code)
        return RedirectResponse(
            url=f"/h5/scan?device_code={code}",
            status_code=302,
        )

    # H5 页面：设备扫码登记
    @app.get("/h5/scan", response_class=HTMLResponse)
    async def h5_scan(request: Request):
        return templates.TemplateResponse(
            "scan.html",
            {"request": request, "app_version": app.version},
        )

    # H5 页面：我的记录
    @app.get("/h5/my-records", response_class=HTMLResponse)
    async def h5_my_records(request: Request):
        undo_hours = max(0, getattr(settings, "UNDO_WINDOW_HOURS", 24))
        return templates.TemplateResponse(
            "my_records.html",
            {"request": request, "app_version": app.version, "undo_window_hours": undo_hours},
        )

    # 后台管理（设备列表、使用记录查询与导出，需管理员登录）
    async def _serve_admin(request: Request):
        return templates.TemplateResponse(
            "admin.html",
            {"request": request, "app_version": app.version},
        )

    @app.get("/admin", response_class=HTMLResponse)
    async def admin_page(request: Request):
        return await _serve_admin(request)

    @app.get("/admin/", response_class=HTMLResponse)
    async def admin_page_trailing(request: Request):
        return await _serve_admin(request)

    app.include_router(routes_auth.router)
    app.include_router(routes_audit.router)
    app.include_router(routes_dashboard.router)
    app.include_router(routes_devices.router)
    app.include_router(routes_dict.router)
    app.include_router(routes_usage.router)
    app.include_router(routes_users.router)

    static_dir = _BASE / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 自定义 /docs：中文标题、说明与青绿色主题，符合院内使用场景
    swagger_params = {
        "docExpansion": "list",
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
        "persistAuthorization": True,
    }
    if (static_dir / "docs-theme.css").exists():
        swagger_params["customCssUrl"] = "/static/docs-theme.css"

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title,
            swagger_ui_parameters=swagger_params,
        )

    return app


app = create_app()

