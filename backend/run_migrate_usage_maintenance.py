"""
一次性迁移：usage_records 表增加维护登记相关列（登记日期、床号、ID号、姓名、关机时间、设备状况、日常保养、终末消毒）。
执行前请备份数据库。执行后可直接删除本文件。

运行方式（在项目根目录，PYTHONPATH 含 backend 的上一级）：
  cd backend && poetry run python run_migrate_usage_maintenance.py
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

# 兼容 SQLAlchemy URL
if url.startswith("postgresql+"):
    url = url.replace("postgresql+psycopg2", "postgresql", 1)

engine = create_engine(url)
is_pg = "postgresql" in url

if not is_pg:
    print("仅支持 PostgreSQL，请手动添加列")
    sys.exit(1)

COLUMNS = [
    ("registration_date", "DATE"),
    ("bed_number", "VARCHAR(32)"),
    ("id_number", "VARCHAR(64)"),
    ("patient_name", "VARCHAR(64)"),
    ("end_time", "TIMESTAMP"),
    ("equipment_condition", "VARCHAR(16)"),
    ("daily_maintenance", "VARCHAR(16)"),
    ("terminal_disinfection", "TEXT"),
]

with engine.connect() as conn:
    for col_name, col_type in COLUMNS:
        r = conn.execute(
            text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'usage_records' AND column_name = :name
            """),
            {"name": col_name},
        )
        if r.fetchone():
            print(f"usage_records.{col_name} 已存在，跳过")
            continue
        conn.execute(text(f"ALTER TABLE usage_records ADD COLUMN {col_name} {col_type}"))
        conn.commit()
        print(f"已添加 usage_records.{col_name}")

    # 可选：为登记日期、床号建索引便于筛选
    try:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_usage_records_registration_date ON usage_records (registration_date)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_usage_records_bed_number ON usage_records (bed_number)"))
        conn.commit()
        print("已创建索引 ix_usage_records_registration_date, ix_usage_records_bed_number")
    except Exception as e:
        print("索引可能已存在或跳过:", e)

print("迁移完成")
