# 数据量与性能说明

当设备数量约 1 万、使用记录约 100 万时，以下优化已生效。

## 已做优化

### 1. 设备列表
- **API**：`GET /api/devices` 支持 `limit`（默认 100，最大 500）、`offset` 分页。
- **总数**：`GET /api/devices/count` 仅返回条数，用于分页展示。
- **联想**：`GET /api/devices/suggest?q=&limit=30` 供筛选区设备/科室下拉，避免一次拉取上万条。

### 2. 使用记录列表
- **API**：`GET /api/usage` 支持 `limit`（默认 100，最大 500）、`offset` 分页。
- **总数**：`GET /api/usage/count` 仅返回条数（与当前筛选条件一致）。

### 3. 使用记录导出
- **单次上限**：符合条件记录超过 **5 万条** 时拒绝导出，提示缩小时间或筛选条件。
- **CSV**：流式生成，按批（每批 5000 条）查询写入，避免百万级一次进内存。
- **Excel/PDF**：仍一次性构建，受 5 万条上限约束。

### 4. 工作台统计
- 设备总数、启用数、使用记录数均通过 **count 接口** 获取，不再全量拉取列表。

### 5. 数据库索引（`create_all` 时会创建）
- **devices**：`(is_active, is_deleted)` 复合索引，便于列表过滤。
- **usage_records**：`(user_id, start_time)`、`(device_code, start_time)` 复合索引，便于按人/按设备按时间查询与分页。

若数据库是**已有库**（表在加索引前就存在），需手动补建索引时可在库中执行：

```sql
-- devices（若尚无该索引）
CREATE INDEX IF NOT EXISTS ix_devices_active_deleted ON devices(is_active, is_deleted);

-- usage_records（若尚无该索引）
CREATE INDEX IF NOT EXISTS ix_usage_user_start ON usage_records(user_id, start_time);
CREATE INDEX IF NOT EXISTS ix_usage_device_start ON usage_records(device_code, start_time);
```

## 建议

- 导出超 5 万条时，引导用户按科室、设备或时间范围分批导出。
- 生产环境建议使用 PostgreSQL，并在 `start_time` 上根据实际查询习惯再评估是否需要单列或更多复合索引。
