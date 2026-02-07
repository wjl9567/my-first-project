# 数据库迁移：支持管理员账号密码登录

本次变更在 `users` 表增加 `username`、`password_hash`，并将 `wx_userid` 改为可空。**仅在已有数据库且表已存在时**需要执行下面 SQL（新库由应用启动时 `create_all` 自动建表，无需执行）。

在 PostgreSQL 中执行：

```sql
-- 新增列（若已存在会报错，可忽略或先检查 information_schema）
ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(64) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- 允许 wx_userid 为空（本地管理员无企微 ID）
ALTER TABLE users ALTER COLUMN wx_userid DROP NOT NULL;
```

若使用 SQLite 或未提供 `IF NOT EXISTS` 的数据库，可逐条执行并跳过已存在的列。
