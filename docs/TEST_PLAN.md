# 医院设备扫码登记系统 - 全维度测试计划

本文档基于项目技术栈（Python + FastAPI + PostgreSQL）与核心业务流程，给出**测试范围、要求、自动化用例与手工验证项**，覆盖功能、异常、接口、数据库、易用性与基础性能。

---

## 一、测试范围总览

| 维度 | 覆盖内容 | 自动化 | 手工/备注 |
|------|----------|--------|-----------|
| 前端交互 | H5 登记页、我的记录、后台管理、扫码/输入设备、表单提交、筛选、撤销 | 页面可访问性 | 扫码流程、提示文案、响应速度需手工/浏览器 |
| 后端接口 | 健康检查、认证、设备 CRUD、使用登记、列表/总数/导出、用户/字典/审计 | ✅ pytest | — |
| 数据库 | 增删改查准确性、外键约束、登记与设备联动、无脏数据 | 通过接口测试间接验证 | 可另做 SQL 抽查 |
| 核心业务 | 扫码后匹配设备、登记后库表同步、维护人即登录人、登记日期/实际时间 | ✅ 部分 | 联动需 E2E |
| 异常场景 | 空值/非法值、无效设备、未登录/越权、重复提交 | ✅ 部分 | 网络中断等需模拟 |
| 性能基础 | 单接口响应时间、批量登记 | 可加 pytest-benchmark 或 locust | 见第五节 |

---

## 二、功能测试

### 2.1 正常流程验证（与需求对照）

- **扫码登记**
  - 步骤：打开 H5 登记页 → 扫一扫或输入设备编号 → 自动带出设备信息 → 填写登记日期、床号、ID 号、姓名、开机/关机时间、设备状况、日常保养、终末消毒 → 提交。
  - 预期：提交成功、提示「登记成功」、数据库 `usage_records` 新增一条，`user_id` 为当前登录用户，`registration_date`/`created_at` 符合设计。
  - 自动化：`test_usage_create_success`、`test_device_create_success`、设备联想 `test_device_suggest`。
- **历史记录与筛选**
  - 步骤：打开「我的记录」→ 按登记日期、床号、设备筛选 → 列表与总数一致。
  - 预期：列表接口与 count 接口在相同筛选条件下一致；撤销后该记录标记已撤销。
  - 自动化：`test_usage_list_success`、`test_usage_count_success`、`test_usage_list_filter_by_bed`。
- **设备信息增删改查**
  - 步骤：管理员创建设备（编号、名称、科室必填）→ 列表/详情/联想/导出/二维码。
  - 预期：创建 201、编号唯一、重复编号 400；列表支持 q、dept、分页；导出 CSV 含表头与数据。
  - 自动化：`test_device_create_success`、`test_device_create_duplicate_code`、`test_device_list_optional_auth`、`test_device_suggest`、`test_device_get_by_id`、`test_device_count`、`test_device_export_csv_success`。
- **数据校验**
  - 设备：编号/名称/科室为空 → 400，提示必填。
  - 登记：**床号、ID 号为选填**（H5 不校验必填，可空提交）；设备不存在 → 404。
  - 自动化：`test_device_create_empty_code`、`test_device_create_empty_name`、`test_usage_create_invalid_device`、`test_usage_create_without_bed_id_optional`。
- **权限控制**
  - 设备创建/更新/导出、用户列表、审计日志、使用记录导出：需管理员（device_admin 或 sys_admin）。
  - 使用记录列表/总数/撤销：需登录，本人仅能撤销自己的记录。
  - 自动化：`test_device_create_requires_admin`、`test_device_patch_requires_admin`、`test_device_export_csv_requires_admin`、`test_usage_create_requires_auth`、`test_usage_list_requires_auth`、`test_usage_export_requires_admin`、`test_usage_undo_requires_auth`、`test_users_list_requires_auth`、`test_audit_list_requires_auth`、`test_dict_create_requires_auth`。

### 2.2 模块间联动

- **扫码后自动匹配设备**：H5 输入或扫码得到 `device_code` → 调用 `GET /api/devices?q=...` 或 `GET /api/devices/{id}` → 表单位置展示设备名称/编号。由前端与接口联调验证；接口侧 `test_device_suggest`、`test_device_get_by_id` 已覆盖。
- **登记后数据库实时同步**：`POST /api/usage` 成功 → 同一会话内 `GET /api/usage` 或 `GET /api/usage/count` 能查到新记录。自动化通过「创建 + 列表/筛选」用例间接覆盖。

---

## 三、异常测试

### 3.1 已覆盖（自动化）

- **空值/非法值**：登录用户名为空/密码为空 → 400；设备编号为空、名称为空 → 400。
- **无效设备**：登记时 `device_code` 不存在 → 404。
- **重复提交**：同一用户、同一设备、短时间内的重复 POST 由后端防重复逻辑返回已有记录（幂等性）；可加用例显式测两次 POST 返回同一条或 201+201 第二条同 id）。
- **未登录/越权**：未带 Token 访问需登录接口 → 401；普通用户访问仅管理员接口 → 403（当前 conftest 为 admin，可新增普通用户 fixture 测 403）。

### 3.2 建议手工或专项模拟

- **扫码失败/无效码**：相机不可用、非本系统二维码、解析失败 → 前端提示清晰、不提交无效设备。
- **数据库连接异常**：关闭 DB 或错误 DATABASE_URL → 接口 500 或连接错误，有统一错误形态，不暴露内部信息。
- **网络中断**：提交中断网 → 前端有加载/错误提示，重试或重新提交不产生脏数据（后端防重复窗口内重复提交已处理）。
- **权限越权**：用普通用户 Token 调设备创建/更新、用户列表、审计、导出 → 403。

---

## 四、接口测试

### 4.1 请求方式、参数、返回格式、状态码

- **健康与根路径**：`GET /health` → 200, `{"status":"ok"}`；`GET /` → 200, `{"message": ...}`。
- **认证**：`POST /api/auth/login` Body `{username, password}` → 200 + `{access_token, token_type}`；空用户名/密码 → 400；错误密码 → 401。`GET /api/auth/me` Header `Authorization: Bearer <token>` → 200 + 用户信息；无 Token → 401。
- **设备**：`POST /api/devices` 需管理员，Body 必填 device_code、name、dept、status；`GET /api/devices`、`GET /api/devices/suggest`、`GET /api/devices/count`、`GET /api/devices/{id}`、`GET /api/devices/{id}/qrcode`、`PATCH /api/devices/{id}`、`GET /api/devices/export` 参数与返回见 OpenAPI，关键状态码已在用例中覆盖。
- **使用记录**：`POST /api/usage` 需登录，Body 含 device_code、usage_type；**bed_number、id_number 为选填（可省略或 null）**；equipment_condition、daily_maintenance 为 normal/abnormal、clean/disinfect。`GET /api/usage`、`GET /api/usage/count` 支持 device_code、registration_date_from/to、bed_number 等；`POST /api/usage/{id}/undo` 需登录且本人；`GET /api/usage/export` 需管理员。
- **用户/字典/审计**：`GET /api/users`、`GET /api/users/count` 需管理员；`GET /api/dict` 可选 dict_type；`POST /api/dict` 需管理员；`GET /api/audit-logs` 需管理员。

### 4.2 幂等性与兼容性

- **登记防重复**：同一用户、同一设备、10 秒内再次 POST 返回已有记录（不重复插入），视为幂等。
- **兼容性**：旧客户端未传维护登记扩展字段时，仍可只传 device_code、usage_type 等，后端兼容；新字段可选。

---

## 五、数据库测试

- **增删改查准确性**：通过接口测试覆盖——创建设备后列表/详情可查；创建登记后列表/count/筛选可查；撤销后 is_deleted 为 true，列表默认不展示（include_deleted 可含）。
- **完整性/一致性**：usage_records.device_code 外键关联 devices.device_code；usage_records.user_id 关联 users.id；设备软删除/停用后，登记列表仍可按 device_code 查到记录，设备详情接口 404。
- **无冗余/脏数据**：测试夹具在用例结束后删除创建的测试设备及关联使用记录，避免长期堆积；可定期抽查 DB 中无 TEST_ 前缀的残留。

---

## 5.1 近期优化验证清单（登记页 + 前后端）

以下针对「床号/ID 号选填」「设备状况/日常保养单选打钩」「必填项红色 \*」等优化的验证方式。

| 项 | 验证内容 | 自动化 | 手工步骤 |
|----|----------|--------|----------|
| 床号、ID 号选填 | 不填床号/ID 号可提交，接口 201，返回/库中该两字段为 null | `test_usage_create_without_bed_id_optional` | 打开 H5 登记页，床号/ID 号留空，其他必填填齐后提交 → 应成功；后台或接口查该条记录 bed_number、id_number 为空 |
| 床号、ID 号占位 | 输入框占位为「选填」，无红色 \* | `test_h5_scan_form_optimizations`（含「选填」） | 打开 `/h5/scan`，确认床号、ID 号旁无 \*，placeholder 为「选填」 |
| 设备状况/日常保养 | 标题无 \*；单选题，选中项为打钩样式（✓） | 同上（含「设备状况」「日常保养」及 normal/abnormal、clean/disinfect） | 确认两项为单选，选中后显示勾选样式；提交后接口返回 equipment_condition、daily_maintenance 正确 |
| 必填项红色 \* | 登记日期、开机时间、关机时间等必填项 label 有 \* | 页面结构在 scan.html 中 `field required` | 目视：仅必填项有 \* |
| 带床号/ID 号提交 | 填写床号、ID 号时仍正常落库 | `test_usage_create_success`、`test_usage_list_filter_by_bed` | 填写床号、ID 号提交 → 列表按床号筛选可查到 |

运行相关自动化用例（在 backend 目录下）：

```bash
poetry run pytest tests/test_usage.py tests/test_pages.py -v
```

---

## 六、易用性/合理性测试（手工）

- **流程简洁**：扫码 → 自动带出设备 → 填表 → 提交，步骤是否最少；是否支持「登记下一台」无需重新扫码。
- **提示清晰**：设备不存在、未登录、权限不足、必填项未填等，前端与接口返回文案是否一致且易懂。
- **操作反馈**：提交中 loading、成功「登记成功」、失败错误信息是否及时且明确。

---

## 七、基础性能测试

- **单接口响应时间**：在本地或测试环境，对 `/health`、`GET /api/devices`、`GET /api/usage`、`POST /api/usage` 等做单次请求，预期 P95 < 500ms（视数据量而定）；可通过 pytest 中记录时间或使用 pytest-benchmark 做趋势对比。
- **批量登记**：连续 N 次 `POST /api/usage`（不同设备或同设备防重复逻辑下），观察响应时间与 DB 无丢失、无重复（防重复窗口内同设备只一条）。
- **可选**：使用 locust 对登录、列表、登记做简单压测，设定并发与 RPS 目标。

---

## 八、如何运行自动化测试

### 8.1 环境要求

- Python 3.10+，Poetry 管理依赖（backend 目录）。
- 已配置 `backend/.env` 或项目根 `.env`：`DATABASE_URL` 指向 PostgreSQL；`ADMIN_USERNAME`、`ADMIN_PASSWORD` 用于测试登录（若未配置则使用默认 admin/admin123，需与库中用户一致或首次登录创建）。
- 数据库已执行迁移（表结构与 `backend/models` 一致，含 usage_records 维护登记字段）。

### 8.2 命令

在 **backend 目录**下执行（PYTHONPATH 指向项目根，以便 `import backend`）：

```bash
# Windows PowerShell
$env:PYTHONPATH = "项目根绝对路径"
poetry run pytest tests -v --tb=short

# Linux / macOS
PYTHONPATH=/path/to/project/root poetry run pytest tests -v --tb=short
```

仅运行部分文件或用例：

```bash
poetry run pytest tests/test_health.py tests/test_usage.py -v
poetry run pytest tests -k "device" -v
```

### 8.3 当前用例清单（46 个，其中 1 个可选跳过）

| 文件 | 用例数 | 说明 |
|------|--------|------|
| test_health.py | 2 | /health, / |
| test_auth.py | 6 | 登录成功/空用户名/空密码/错误密码，/me 无 Token/成功 |
| test_devices.py | 11 | 设备创建权限/成功/重复编号，列表/联想/详情/404，更新权限，count，导出权限/成功 |
| test_devices_validation.py | 2 | 设备编号为空、名称为空 → 400 |
| test_usage.py | 11 | 登记需登录/无效设备 404/成功/重复提交幂等，列表/总数需登录/成功，导出权限/成功，撤销需登录，按床号筛选 |
| test_users.py | 3 | 用户列表需登录、管理员成功、count |
| test_dict.py | 3 | 使用类型/设备状态列表，新增需权限 |
| test_audit.py | 2 | 审计列表需登录、管理员成功 |
| test_pages.py | 3 | H5 登记、我的记录、后台管理页 200 且含 HTML |
| test_performance_basic.py | 3 | /health、/ 单次请求 2s 内（其中 test_health_latency 默认 skip，可选启用） |

---

## 九、测试通过标准

- **自动化**：上述 pytest 用例全部通过，无未处理异常。
- **功能**：核心流程（扫码登记、历史筛选、设备 CRUD、导出）与需求一致，数据落库正确。
- **异常**：空值/非法值/无效设备/未登录/越权返回符合规范状态码与文案。
- **接口**：请求方法、参数、返回格式、状态码符合 OpenAPI/设计；登记防重复满足幂等。
- **数据库**：无外键违反、无测试数据长期残留（TEST_ 设备在用例后清理）。
- **易用性**：流程简洁、提示清晰、反馈及时（以手工验收为准）。
- **性能**：单次核心接口响应在可接受范围内（可先定 500ms～1s 为参考，再按环境调优）。

本文档与 `backend/tests/` 下的用例共同构成全维度测试方案，后续可随需求补充 E2E（如 Playwright）、性能脚本与数据库专项检查。
