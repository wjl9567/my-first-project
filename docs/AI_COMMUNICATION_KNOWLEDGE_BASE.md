# AI 高效沟通知识库

> 基于实际项目对话提炼的「问题类型 × 技术场景」双维度知识库，便于后续查阅与指令复用。

---

## 零、项目技术路线（全栈评估摘要）

本小节为**全栈技术路线**的固定说明，便于 AI 与人在同一技术上下文中沟通；做需求或排错时可直接引用「按当前技术路线」。

### 0.1 整体架构

| 维度 | 选型 | 说明 |
|------|------|------|
| **形态** | 前后端一体、服务端渲染 | 无独立前端工程，页面由后端 Jinja2 渲染 HTML，前端为内联/同目录 JS |
| **后端语言** | Python 3.10+ | 类型注解、async 可选，统一 3.10 以上 |
| **Web 框架** | FastAPI | 路由、依赖注入、OpenAPI、请求体验证（Pydantic） |
| **运行方式** | Uvicorn（ASGI） | 单进程；生产可配多 worker 或反向代理后单实例 |

### 0.2 后端技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **依赖与环境** | Poetry | 依赖管理、虚拟环境；项目在 `backend/`，venv 默认 `backend/.venv` |
| **ORM / 数据库** | SQLAlchemy 2.x + PostgreSQL | `psycopg2-binary` 驱动；`DeclarativeBase`、Mapped、session 注入 |
| **配置** | python-dotenv | 从**项目根**工作目录下的 `.env` 加载（部署时 .env 在项目根） |
| **认证** | JWT（PyJWT）+ 企业微信 OAuth | Bearer Token；企微仅做身份获取，角色在 DB（user/device_admin/sys_admin） |
| **密码** | Passlib（bcrypt） | 仅本地管理员登录使用 |
| **HTTP 客户端** | httpx | 企微 API 调用，带超时 |
| **其他** | qrcode、openpyxl、reportlab、Jinja2 | 设备二维码、Excel/PDF 导出、模板渲染 |

### 0.3 前端技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **页面** | Jinja2 服务端渲染 | 模板在 `backend/templates/`（admin.html、scan.html、my_records.html） |
| **脚本** | 原生 JavaScript（ES5 风格） | 无构建、无 npm；`fetch`、DOM、`localStorage`（如 token、列宽缓存） |
| **样式** | 内联 `<style>` + 少量 class | 统一 CSS 变量（主色、圆角、阴影），移动端适配 viewport、safe-area |
| **H5 能力** | 摄像头 + jsQR | 扫码页使用 `getUserMedia` + jsQR 解析二维码 |
| **兼容** | 现代浏览器 + 企业微信内嵌 | 不依赖 IE；需兼容 Chrome/Edge/Firefox 及企微内置浏览器 |

### 0.4 数据与模型（核心表）

| 表/模块 | 说明 |
|---------|------|
| **users** | 用户；企微 wx_userid 或本地 username/password_hash；role：user / device_admin / sys_admin |
| **devices** | 设备；device_code 唯一、软删除 is_deleted、启用 is_active、状态 status（字典码） |
| **usage_records** | 使用记录；device_code、user_id、usage_type（字典码）、start_time、note 等 |
| **dict_items** | 字典；dict_type（如 usage_type、device_status）、code、label、is_active、is_deleted |
| **audit_logs** | 审计；actor_id、action（如 device.create）、target_type、target_id、target_code、details、created_at |

**约定**：设备相关审计的 `details` 带 `device_code=XXX`；列表接口对 `target_type=device` 可返回 `target_code` 供前端展示。

### 0.5 安全与部署约定

| 项 | 约定 |
|----|------|
| **JWT** | 生产必须设置非默认 `JWT_SECRET`；`ENVIRONMENT=production` 时使用默认值则拒绝启动 |
| **院内访问** | 可选 `ALLOWED_ADMIN_ORIGINS` / `ALLOWED_ADMIN_IPS`，限制 /admin、/docs、管理员登录来源 |
| **企微** | BASE_URL 需 HTTPS，与企微可信域名一致；state 仅允许相对路径防开放重定向 |
| **部署** | 工作目录为**项目根**；PYTHONPATH=项目根；`.env` 在项目根；systemd + Nginx 反向代理（见 docs/DEPLOYMENT.md） |

### 0.6 与 AI 协作时的用法

- **需求描述**：可先说「按当前技术路线」，再写具体需求（如「H5 登记页设备编码校验」「管理端表头列宽拖拽」），避免 AI 提议换框架或栈。  
- **排错/扩展**：指明模块（如 `routes_usage`、`schemas.UsageRecordCreate`），便于在现有技术选型下改代码。  
- **文档**：技术路线变更时同步更新本节，保持知识库与项目一致。

---

## 一、AI 编程指令优化

### 1.1 前端交互需求描述

| 要素 | 说明 |
|------|------|
| **触发时机** | 明确在什么操作下触发（如：失焦、扫码完成、点击提交） |
| **校验/逻辑** | 写清「谁调谁」、成功/失败分别做什么（提示、清空、禁用、聚焦） |
| **体验约束** | 字体、颜色、不遮挡、无卡顿、即时生效、本地缓存等 |

**原始问题示例**  
> 开发前端移动端「设备使用登记」页面的设备编码校验功能……

**优化后的精准指令**  
- 触发时机：① 手动输入设备编码并失去焦点时；② 扫描设备编码完成后。  
- 校验逻辑：调用后端接口校验；若不存在或已删除 → 输入框下方红色提示、清空除设备编码外的表单、聚焦回编码框、禁用提交；若有效 → 隐藏提示、恢复提交。  
- 体验：提示 14px、不遮挡、清空即时生效。

**核心结论**  
- **先写「何时触发」，再写「成功/失败分支」，最后写「体验约束」**，AI 能一次性给出完整实现（DOM 结构、样式、事件、状态函数）。

---

### 1.2 后端功能需求描述

| 要素 | 说明 |
|------|------|
| **数据流** | 谁写入、谁读取、存什么字段、返回什么结构 |
| **边界** | 不存在/已删除/无权限时的行为（404、422、过滤条件） |
| **一致性** | 与现有 API、表结构、前端展示是否一致 |

**原始问题示例**  
> 审计日志里备注要带设备编码；修改项：启用状态 还是无法知道修改的哪台设备。

**优化后的精准指令**  
- 后端：设备相关 `log_audit` 的 `details` 中写入 `device_code=XXX`；列表接口对 `target_type=device` 时查设备表填充 `target_code` 返回。  
- 前端：从 `details` 或 `r.target_code` 解析设备编码，优先展示「设备{编码}」，无编码时兜底「设备 ID {id}」。

**核心结论**  
- **明确「写到哪里、读从哪里来、展示格式」**，可避免只改一端导致前后端不一致。

---

### 1.3 全站级逻辑与一致性

**原始问题示例**  
> 请检查全站，这类事务逻辑错误的地方有没有需要优化的。

**优化后的精准指令**  
- 问题类型：业务写与审计写（或其它二次写）是否应同事务。  
- 范围：全站所有「先 commit 再 log_audit」的接口。  
- 目标：业务 + 审计同一事务提交，或明确说明为何分离。

**核心结论**  
- **先定义「这类错误」的判定标准，再限定「全站/某模块」**，便于 AI 系统性搜索并逐处修改。

---

## 二、项目开发技巧

### 2.1 审计日志与设备编码

**原始问题**  
审计日志的备注里，设备相关操作要能看出是哪台设备；数值如「修改项：启用状态」无法对应到具体设备。

**优化后的精准指令**  
1. 后端：设备新增/修改/删除/恢复时，`log_audit` 的 `details` 均带 `device_code=XXX`；列表接口对设备类型记录返回 `target_code`（设备编码）。  
2. 前端：设备相关操作备注优先展示「设备{编码}」，无编码时展示「设备 ID {id}」。

**核心结论 / 代码示例**

- **后端 details 格式**：`device_code={device.device_code}`，修改时可追加 `,name,dept` 等修改项。  
- **前端解析**：从 `details` 或接口返回的 `target_code` 取编码，统一用「设备XXX」展示。

```javascript
// 前端：设备展示优先编码
function deviceLabelFromAuditRow(r, parsed) {
  var code = (parsed && parsed.code) ? parsed.code : (r.target_code != null ? String(r.target_code) : "");
  return code ? "设备" + code : (r.target_id != null ? "设备 ID " + r.target_id : "");
}
```

---

### 2.2 事务逻辑：业务写与审计写同事务

**原始问题**  
先操作设备停用、再新增设备，审计日志里没有记录。

**优化后的精准指令**  
- 现象：审计未写入。  
- 原因：业务 `commit` 与 `log_audit` 的 `commit` 分离，若后者失败或未执行会漏记。  
- 要求：设备新增/更新、登录创建用户等「业务写 + 审计写」放在同一事务，一次 `commit`。

**核心结论 / 代码示例**

- **`log_audit` 增加参数 `do_commit=True`**：`do_commit=False` 时只 `db.add(entry)` 不提交，由调用方统一 `commit`。  
- **调用方**：先 `db.add(业务实体)`、必要时 `db.flush()`，再 `log_audit(..., do_commit=False)`，最后 `db.commit()`。

```python
# audit.py
def log_audit(..., do_commit: bool = True):
    db.add(entry)
    if do_commit:
        db.commit()

# routes_devices.py 新增设备
db.add(device)
db.flush()
log_audit(db, current_user.id, "device.create", "device", device.id, f"device_code={device.device_code}", do_commit=False)
db.commit()
db.refresh(device)
```

---

### 2.3 设备列表「只显示已删除」与导出

**原始问题**  
「显示已删除」改为「只显示已删除」哪种更适合用户？

**优化后的精准指令**  
- 需求：勾选后列表**仅**显示已删除设备，便于找回并恢复；不勾选为正常列表。  
- 后端：增加 `deleted_only` 参数；为 true 时筛选 `is_deleted=True`，且不按启用状态过滤。

**核心结论**

- **「只显示已删除」** 更符合「恢复误删设备」场景；后端用 `deleted_only` 单独分支查询，导出/列表/count 均支持该参数。

---

### 2.4 导出日期格式与系统展示一致

**原始问题**  
导出功能涉及日期时，按系统查询展示出来的格式导出。

**优化后的精准指令**  
- 要求：导出 CSV/Excel/PDF 中的日期时间与「查询列表」展示格式一致。  
- 格式：`YYYY-MM-DD HH:mm:ss`（不用 ISO 的 `T` 分隔）。

**核心结论 / 代码示例**

- **统一用 `strftime` 输出展示格式**，不在导出里用 `isoformat()`。

```python
# 使用记录导出
_DISPLAY_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
def _format_display_datetime(dt): ...
# 设备导出
d.created_at.strftime("%Y-%m-%d %H:%M:%S") if d.created_at else ""
```

---

### 2.5 表头列宽拖拽与本地缓存

**原始问题**  
设备管理页表头列支持鼠标拖拽调整列宽，列宽要缓存，有最小/最大限制。

**优化后的精准指令**  
- 交互：列右边缘拖拽手柄，光标 `col-resize`，拖拽即时改宽。  
- 约束：最小 80px，最大屏幕宽度 50%；`table-layout: fixed` + `<col>` 控制列宽。  
- 持久化：列宽存 `localStorage`，key 如 `device_scan_cols_{tableId}`，刷新后恢复。

**核心结论**

- **用 `<colgroup>`+`<col style="width:...">` 控制列宽**；拖拽只改对应 `col` 的 width 并写缓存；边界在 `mousemove` 里用 `Math.max(MIN, Math.min(MAX, newW))` 限制。

---

### 2.6 API 422 与请求体验验校验

**原始问题**  
`POST /api/usage` 返回 422 Unprocessable Content。

**优化后的精准指令**  
- 现象：提交登记时报 422。  
- 可能原因：必填字段缺失或类型不符（如 `usage_type` 为 null/空导致校验失败）。  
- 要求：前端提交前校验必填项并提示；后端对可兼容字段（如 `usage_type` 空）做默认值或友好校验。

**核心结论 / 代码示例**

- **前端**：提交前检查 `usage_type` 等，非法时提示「请先选择使用类型」并中止请求。  
- **后端**：对 `usage_type` 做 `mode="before"` 的 validator，`None`/空时默认 1，避免 422。

```python
# schemas.py UsageRecordCreate
@field_validator("usage_type", mode="before")
@classmethod
def usage_type_coerce(cls, v): ...
    if v is None or v == "": return 1
```

---

### 2.7 H5 分页与「加载更多」

**原始问题**  
H5 页面是否需要处理分页功能，比如「我的记录」？

**优化后的精准指令**  
- 现状：接口默认 limit=100，前端又只展示前 30 条，超出看不到。  
- 要求：首屏拉一页（如 30 条）+ 总数（count），底部「加载更多」拉下一页并追加；无更多时隐藏按钮。

**核心结论**

- **需要分页**：用 `GET /api/usage?limit=30&offset=...` 和 `GET /api/usage/count`；前端维护 `recordsLoaded` 与 `totalCount`，`hasMore = recordsLoaded.length < totalCount` 或本页条数 < pageSize 时隐藏「加载更多」。

---

## 三、工具与效率

### 3.1 需求拆解与一次到位

**可复用句式**

- **功能类**：「在 [页面/模块] 实现 [功能]；触发时机：[…]；成功时：[…]；失败时：[…]；体验要求：[…]。」  
- **修复类**：「[现象]；可能原因：[…]；请检查 [范围] 并修复，要求 [约束]。」  
- **全站类**：「请检查全站/本模块，[某类问题] 的地方，并给出修改方案。」

**核心结论**

- **触发时机 + 成功/失败分支 + 体验/边界** 写全，能减少多轮追问，一次得到完整实现。

---

### 3.2 代码修改的精准引用

**建议**

- 提需求时附带 **文件路径 + 关键函数/行号**（如「`backend/routes_devices.py` 的 `update_device` 里三处 `log_audit`」），便于 AI 直接定位。  
- 修改后如需扩展，说明「在刚才的 X 基础上，再增加 Y」，便于延续上下文。

---

## 四、快速索引

| 场景 | 关键词 | 对应章节 |
|------|--------|----------|
| **技术路线/全栈选型** | FastAPI、PostgreSQL、Jinja2、JWT、Poetry、.env 位置 | **零** |
| 前端交互/校验 | 触发时机、提示、禁用、聚焦 | 1.1、2.7 |
| 审计/设备编码 | device_code、target_code、备注 | 1.2、2.1 |
| 事务/审计漏记 | log_audit、do_commit、同事务 | 2.2、1.3 |
| 设备列表筛选 | deleted_only、只显示已删除 | 2.3 |
| 导出格式 | 日期、strftime、展示一致 | 2.4 |
| 表头拖拽 | 列宽、localStorage、min/max | 2.5 |
| 422/校验 | usage_type、field_validator | 2.6 |
| H5 分页 | 加载更多、limit、offset、count | 2.7 |
| 指令写法 | 需求拆解、精准引用 | 3.1、3.2 |

---

*文档由对话提炼生成；技术路线见「零」，可直接保存为 `.md` 查阅与复用。*
