# 医院设备扫码登记系统 — 精简需求规格说明书（SRS）

版本：1.0
日期：2026-02-06
作者：产品/需求方（示例）
仓库：wjl9567/my-first-project

目标简介
- 在企业微信内通过扫码设备二维码完成设备使用登记，替换纸质登记本。
- 记录使用人、时间、用途、照片/备注，支持后台导出。

范围（MVP）
包含
- 二维码生成并导出 PDF/标签供打印。
- 企业微信 H5 扫码页面（扫码→填表→提交）。
- 后台管理（Web，管理员用）：设备管理、使用记录查询与导出（CSV）。
- 基本审计日志（记录操作人、时间、来源）。
不包含（MVP 之外）
- 与 HIS 等系统自动对接。
- 复杂工作流或工单系统。

主要角色与权限
- 普通用户（护士/技师）：通过企业微信扫码并登记，查看本人最近记录。
- 设备管理员：新增/编辑设备、生成二维码 PDF、查看/导出记录。
- 系统管理员：管理���号与权限、查看审计日志。

核心功能
1. 设备与二维码
- 设备基础信息：设备编号、名称、科室/位置、状态、负责人。
- 生成唯一二维码（设备ID或深度链接），导出 PDF。

2. 扫码登记（核心）
- 企业微信 H5 支持摄像头扫码或手动输入设备ID。
- 扫描后显示设备信息并打开登记表单，自动填充当前企业微信用户与服务器时间。
- 最小登记字段：使用人（当前用户）、使用时间、使用类型（常规/借用/维修/校准/其它）、病历号或备注（可选）、照片上传（可选）。
- 支持一键快速登记（扫码后点击确认）。

3. 查询与导出
- 管理端按设备/时间/使用人导出 CSV。
- 普通用户可查看近 N 条个人记录。

4. 身份与认证
- 使用企业微信登录（OAuth），通过企业微信 ID 映射系统用户。

5. 审计与日志
- 记录创建者、时间、来源（wecom 应用 ID / IP）、附件URL。

离线考虑（可选）
- 如需支持无网场景，可在 H5 使用本地缓存（IndexedDB）并实现重试同步。推荐初期先不实现复杂离线策略。

简要数据模型
- users: id, wx_userid, real_name, role, dept
- devices: id, device_code, name, dept, location, status, qr_value, created_by, created_at
- usage_records: id, device_id, user_id, usage_type, patient_id_or_note, photo_urls[], created_at, source
- audit_logs: id, actor_id, action, target_type, target_id, details, created_at

简化 API 设计（示例）
- GET /api/devices/:id
- POST /api/devices (管理员)
- POST /api/devices/:id/qrcode -> 返回 PDF
- POST /api/usage -> 保存使用记录
- GET /api/usage?device_id=&from=&to=&user_id= -> 导出 CSV
认证：企业微信 OAuth token（Bearer）

用户界面要点
- 企业微信 H5: 扫描页、登记表单、提交成功页、查看记录。
- 后台管理: 设备列表（新增/编辑/生成二维码）、使用记录查询与导出、用户与权限管理。

安全与隐私（最小要求）
- 全部通信使用 HTTPS/TLS。
- 附件存储使用受控访问（短期签名 URL）。
- 最小化患者敏感字段存储，支持脱敏/加密。

验收标准（MVP）
- 企业微信内扫码后 5 秒内显示表单（局域网内）。
- 保存的记录在后台可检索（包含时间、用户、设备）。
- 管理端能生成并下载二维码 PDF。
- 管理端能按设备/时间导出 CSV。
- 企业微信登录映射用户并可配置管理员权限。

部署建议
- 架构：企业微信 H5 + 后端 API + PostgreSQL + 对象存储。
- 推荐先单实例部署完成 MVP，后续容器化扩展。

里程（示例）
- 需求确认与原型：2 天
- 后端与 DB：4-6 天
- 企业微信 H5：3-5 天
- 后台管理：3-5 天
- 测试与 UAT：2-3 天
- MVP 总计约 2-3 周（视团队和审批）

下一步建议
- 我可以现在开始把本 SRS 提交到仓库，并继续协助创建项目骨架（API 文档、基本后端/前端样板、CI 配置）或先等你确认技术栈（推荐 Node.js + Express + PostgreSQL 或 Python + FastAPI + PostgreSQL）。

附：样例 POST /api/usage 请求体
```json
{
  "device_id": "DE-2026-000123",
  "user_id": "wx-12345",
  "usage_type": "routine",
  "patient_id": "P-2026-00001",
  "start_time": "2026-02-06T09:15:00+08:00",
  "notes": "用于心电监护，设备运行正常",
  "photo_urls": []
}
```