# 文档目录与改动摘要

本目录存放项目说明与变更记录。下文为根据《全栈代码评估报告》完成的改动摘要。

---

## 根据评估报告完成的改动摘要

### 一、后端

#### 1. 院内访问控制（必须）
- **`backend/config.py`**：新增 `ALLOWED_ADMIN_ORIGINS`、`ALLOWED_ADMIN_IPS`、`WECOM_HTTP_TIMEOUT`，以及 `get_allowed_admin_origins()`、`get_allowed_admin_ips()`。
- **`backend/admin_access.py`**（新文件）：实现来源校验逻辑（Origin/Referer 前缀匹配、IP/CIDR 白名单），并对 `/admin`、`/docs`、`POST /api/auth/login` 做校验；配置为空时不拦截，便于开发。
- **`backend/main.py`**：注册 `AdminAccessMiddleware`。

#### 2. JWT_SECRET 生产加固（必须）
- **`backend/config.py`**：将默认值抽成常量 `JWT_SECRET_DEFAULT`。
- **`backend/main.py`**：增加 `startup` 事件：若 `JWT_SECRET` 仍为默认值则打 warning；若 `ENVIRONMENT=production` 且为默认值则**拒绝启动**并抛 `RuntimeError`。

#### 3. 企业微信 state 校验（建议）
- **`backend/routes_auth.py`**：在 `wecom_callback` 中校验 `state`：仅允许以 `/` 开头且不含 `//` 的相对路径，否则重定向使用默认 `next_path="/h5/scan"`，避免开放重定向。

#### 4. httpx 超时（建议）
- **`backend/auth.py`**：两处 `httpx.Client()` 均增加 `timeout=getattr(settings, "WECOM_HTTP_TIMEOUT", 10.0)`。

#### 5. 种子数据异常日志（建议）
- **`backend/main.py`**：字典种子写入的 `except Exception` 改为 `_logger.exception("字典种子数据写入失败")`，便于排查。

#### 6. 配置说明
- **`backend/.env.example`**：补充 `ENVIRONMENT`、`ALLOWED_ADMIN_ORIGINS`、`ALLOWED_ADMIN_IPS`、`WECOM_HTTP_TIMEOUT` 的说明与示例。

---

### 二、前端（XSS 修复）

#### 1. 统一 HTML 转义
- **`backend/templates/admin.html`**、**`backend/templates/my_records.html`**：在脚本开头增加 `escapeHtml(s)`（转义 `& < > " '`），所有写入 `innerHTML` 的接口/用户数据均先经 `escapeHtml` 再拼接。

#### 2. 已覆盖的展示位置
- **admin.html**：设备表格（编号、名称、科室、状态）、设备编辑输入框、使用记录表格（时间、设备、使用人、类型、备注）、审计日志（时间、操作人、操作说明、备注）、字典表格（编码、显示名称、状态、已删除、编辑按钮的 `data-label` 及编辑框）、设备 suggest 的 option 使用 `textContent` 赋值。
- **my_records.html**：我的记录卡片中的时间、设备信息、类型、备注。

#### 3. scan.html
- 设备信息使用 `textContent`，使用类型选项使用 `createElement` + `opt.textContent = item.label`，未发现需要改动的 `innerHTML` 插入接口数据。

---

### 三、使用与注意

1. **院内访问控制**  
   - 生产环境在 `.env` 中配置 `ALLOWED_ADMIN_ORIGINS` 和/或 `ALLOWED_ADMIN_IPS`（例如 `ALLOWED_ADMIN_ORIGINS=https://admin.xxx.edu.cn`，`ALLOWED_ADMIN_IPS=192.168.0.0/16`）。  
   - 不配置则不做校验，所有来源均可访问 `/admin`、`/docs` 和管理员登录接口。

2. **生产环境启动**  
   - 设置 `ENVIRONMENT=production` 且未设置有效的 `JWT_SECRET` 时，应用将拒绝启动，需在环境中配置非默认的 `JWT_SECRET`。

3. **企业微信回调**  
   - 仅接受“以 `/` 开头且不含 `//`”的 `state`，否则按默认跳转 `/h5/scan`，避免被利用做开放重定向。

---

## 其他文档

| 文档 | 说明 |
|------|------|
| [DEPLOYMENT.md](./DEPLOYMENT.md) | **上线部署详细步骤**（环境、配置、systemd、Nginx、检查清单） |
| [CODE_REVIEW_REPORT.md](./CODE_REVIEW_REPORT.md) | 全栈代码评估报告（功能、规范、性能、健壮性、安全、可维护性及优化建议） |
| [SCALING_AND_INDEXES.md](./SCALING_AND_INDEXES.md) | 数据量与性能说明（分页、导出上限、索引等） |
| [DB_MIGRATION_ADMIN_LOGIN.md](./DB_MIGRATION_ADMIN_LOGIN.md) | 管理员登录相关数据库迁移说明 |
| [WECOM_SETUP.md](./WECOM_SETUP.md) | 企业微信接入配置说明 |
