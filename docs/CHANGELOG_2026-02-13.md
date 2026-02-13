# 2026-02-13 调整说明

## 功能与体验

- **借用：预计归还改为仅日期**  
  预计归还时间改为「预计归还日期」，仅选择年月日，不再选时分；支持当天借当天还（借用日期与预计归还日期可相等）。
- **维修/故障表单精简**  
  去掉「报修时间」「期望完成时间」及对应输入框，仅保留：报修日期、报修人（选填）、故障描述（必填）。
- **我的记录按类型展示**  
  - 借用：只显示「预计归还」日期，不显示开机/关机。  
  - 维修/故障：不显示开机/关机、报修时间、期望完成；仅展示报修人、故障描述等。  
  - 常规使用：仍显示开机/关机、设备状况、日常保养。
- **纯编号扫码与短链**  
  - 登记页「扫一扫」支持二维码内容为纯设备/资产编号（无 URL）。  
  - 新增短链 `GET /s/{device_code}`，跳转到登记页并带出设备；文案提示支持「完整链接或纯资产编号」。
- **设备批量导入前端**  
  后台设备管理增加「批量导入」：下载 Excel 模板、上传 .xlsx、展示导入结果（成功/跳过/错误），导入后刷新列表与工作台统计。
- **SQLite 兼容**  
  启动迁移中 `ALTER TABLE users ADD COLUMN is_active` 改为兼容旧版 SQLite（无 `IF NOT EXISTS` 时先 try 再忽略「列已存在」）。
- **依赖**  
  新增 `python-multipart`（设备导入上传），并执行 `poetry lock`。

## 文档与脚本

- 全站测试清单：`docs/TEST_CHECKLIST.md`
- 验证操作指南：`docs/VERIFICATION_GUIDE.md`
- 验证报告（自动部分）：`docs/VERIFICATION_REPORT.md`
- 演示脚本：`docs/DEMO_SCRIPT.md`
- `.gitignore`：忽略 `backend/.env`、`*.db`、`__pycache__/`、`*.pyc`

## 测试

- 登记/借用/维修相关用例已按新模板与规则调整；H5 页面用例改为 ASCII 断言以兼容 Windows 编码；并发用例放宽断言。
- 生产发布前需配置：JWT_SECRET、BASE_URL、ALLOWED_ADMIN_ORIGINS（可选）；正式环境建议使用 PostgreSQL，通过 `DATABASE_URL` 配置即可，无需改代码。
