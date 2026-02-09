"""
一次性迁移：usage_records 表增加 is_deleted 列，用于用户「撤销」登记（软删除）。
执行前请备份数据库。执行后可直接删除本文件。

运行方式（在 backend 目录下）：
  poetry run python run_migrate_usage_soft_delete.py
"""
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    print("未设置 DATABASE_URL")
    sys.exit(1)

engine = create_engine(url)
is_pg = "postgresql" in url

with engine.connect() as conn:
    if is_pg:
        r = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'usage_records' AND column_name = 'is_deleted'
        """))
        if r.fetchone():
            print("usage_records.is_deleted 已存在，跳过")
            sys.exit(0)
        conn.execute(text("""
            ALTER TABLE usage_records ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT false
        """))
        conn.commit()
        print("已添加 usage_records.is_deleted")
    else:
        print("仅支持 PostgreSQL，请手动添加 is_deleted 列")
        sys.exit(1)
