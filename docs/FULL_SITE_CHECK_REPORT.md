# 全站检查报告

检查时间：基于当前代码库静态检查与逻辑梳理。

---

## 一、已修复的小问题

- **main.py**：`@app.on_event("startup")` 与 `@app.get("/health")` 之间补上换行，避免格式混乱。

---

## 二、弃用与技术债（建议后续处理）

| 位置 | 说明 |
|------|------|
| **main.py** | `@app.on_event("startup")` 已弃用，FastAPI 建议改用 lifespan 上下文管理器，后续可迁移。 |
| **schemas.py** | 多处 `class Config: from_attributes = True`，Pydantic v2 建议改用 `model_config = ConfigDict(from_attributes=True)`，消除弃用告警。 |
| **models.py** | `datetime.utcnow` 已弃用，建议改为 `datetime.now(timezone.utc)` 或等效写法。 |
| **Jinja2 TemplateResponse** | 若使用 Starlette 新版本，需确认 `TemplateResponse(request, name, context)` 的签名（request 是否为首参），当前用法若报弃用再改。 |

以上不影响当前功能，仅建议在合适版本升级时一并处理。

---

## 三、潜在问题与边界情况

| 类别 | 位置/场景 | 说明与建议 |
|------|-----------|------------|
| **H5 登记** | 未选操作类型即提交 | 前端已校验“请先选择操作类型以加载表单”；若用户快速连续点击，可考虑防抖或提交中禁用按钮（当前已有 `submitBtn.disabled`）。 |
| **H5 登记** | 选择操作类型后未拉取到 form-schema | 已做 catch 回退到 normal 模板；若接口长期失败，可考虑前端提示“加载表单失败，请刷新”。 |
| **字典** | GET /api/dict 无鉴权 | 当前设计为 H5 登记页需拉取 usage_type 下拉，故列表接口未强制登录；若后续需限制仅登录可见，再改为可选鉴权或白名单。 |
| **设备** | 老库无 is_deleted 列 | routes_devices 已用 `_devices_table_has_is_deleted()` 做兼容，迁移后无问题。 |
| **run.py** | host=127.0.0.1 | 仅本机可访问；若需局域网访问后台，需改为 `0.0.0.0` 或通过 Nginx 等反向代理。 |
| **start_local.py** | 无 KeyboardInterrupt 处理 | 与 run.py 一致可加 try/except KeyboardInterrupt，避免 Ctrl+C 时堆栈刷屏（可选）。 |

---

## 四、安全与配置

| 项 | 状态与建议 |
|----|------------|
| **JWT_SECRET** | 生产环境必须在环境变量中设置且不可为默认值（main 启动时已校验）。 |
| **ADMIN_USERNAME / ADMIN_PASSWORD** | 未配置时无法使用本地管理员登录；生产务必配置并保证强度。 |
| **ALLOWED_ADMIN_ORIGINS / ALLOWED_ADMIN_IPS** | 为空时不校验，开发方便；生产建议配置院内来源或 IP 白名单。 |
| **企业微信** | WECOM_* 未配置时企业微信登录返回 503，H5 仍可依赖本地管理员登录（同一浏览器先登后台再访问 H5）。 |
| **密码** | 使用 bcrypt，长度截断 72 字节，实现合理。 |
| **SQL/模板注入** | 使用 ORM 与 Jinja2 默认转义，未发现明显注入点。 |

---

## 五、稳定性与健壮性

| 项 | 说明 |
|----|------|
| **数据库连接** | 未设置 `pool_pre_ping` / `pool_recycle`；长运行或数据库重启后可能偶发断连，可考虑在 create_engine 中增加。 |
| **企业微信 token 缓存** | auth 模块内存缓存 access_token，多进程/多实例部署时各自缓存，可能重复拉 token，可接受；若需统一可改用 Redis。 |
| **防重复提交** | 使用记录 10 秒内同用户同设备防重复，逻辑正确。 |
| **撤销窗口** | UNDO_WINDOW_HOURS 可配置，默认 24 小时，合理。 |

---

## 六、前后端一致性

| 项 | 状态 |
|----|------|
| **usage_type** | 字典与 form_templates 映射一致（1 常规 2 借用 3 维修 4 校准 5 其他）；DictItemRead.code 序列化为 int，前端用 String(it.code) 兼容。 |
| **借用/维修 payload** | 前端 buildPayloadByTemplate 与 UsageRecordCreate 字段一致（dept_at_use、note、start_time、end_time 等）。 |
| **datetime 格式** | 前端传 ISO 字符串，后端 parse_naive_as_china_then_utc 按中国时区解析，逻辑一致。 |

---

## 七、测试与部署

| 项 | 建议 |
|----|------|
| **测试** | 在 backend 目录下执行 `PYTHONPATH=.. poetry run pytest backend/tests -v` 做回归；当前用例覆盖主要接口与权限。 |
| **部署** | 生产建议用 gunicorn/uvicorn 多 worker + Nginx 反向代理；run.py 的 reload=True 仅适合开发。 |
| **静态与模板** | 模板与静态资源随后端部署，无需单独前端构建。 |

---

## 八、小结

- **功能**：扫码 → 设备回填 → 操作类型 → 差异化表单 → 校验 → 提交 → 跳转/我的记录 流程完整；字典与科室模板扩展点已预留。
- **已修**：main.py 格式问题。
- **建议优先**：生产环境配置 JWT_SECRET、ADMIN_*、ALLOWED_*；长运行可加数据库连接池参数；按需将 on_event 与 Pydantic/Model 配置迁移到推荐写法。
- **可选**：start_local 与 run 的 Ctrl+C 友好退出、form-schema 失败时的前端提示、数据库 pool 参数。
