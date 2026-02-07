"""
一次性迁移：usage_records 表用 device_code 存设备标识，与 devices.device_code 一致。
- 添加 device_code 列并从未有数据回填
- 删除 device_id 列
- 建立 device_code 外键（PostgreSQL）

执行前请备份数据库。执行后可直接删除本文件。
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
    # 检查是否已有 device_code 列（已迁移过则跳过）
    if is_pg:
        r = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'usage_records' AND column_name = 'device_code'
        """))
        if r.fetchone():
            print("usage_records 已有 device_code 列，跳过迁移。")
            sys.exit(0)
    else:
        # SQLite
        r = conn.execute(text("PRAGMA table_info(usage_records)"))
        if any(row[1] == "device_code" for row in r.fetchall()):
            print("usage_records 已有 device_code 列，跳过迁移。")
            sys.exit(0)

    # 1. 添加 device_code 列
    conn.execute(text("ALTER TABLE usage_records ADD COLUMN device_code VARCHAR(64)"))
    conn.commit()

    # 2. 从 device_id 回填 device_code（无对应设备的记录保留 device_code 为空，后续设 NOT NULL 前需处理）
    conn.execute(text("""
        UPDATE usage_records u
        SET device_code = (SELECT d.device_code FROM devices d WHERE d.id = u.device_id)
        WHERE u.device_id IS NOT NULL
    """))
    conn.commit()
    # 若有孤儿记录（device_id 指向已删设备），可删除或忽略；设 NOT NULL 前仅对已有 device_code 的行有效
    if is_pg:
        conn.execute(text("DELETE FROM usage_records WHERE device_code IS NULL"))
        conn.commit()

    # 3. 删除 device_id 列（PostgreSQL 用 CASCADE 同时删除该列上的外键）
    if is_pg:
        conn.execute(text("ALTER TABLE usage_records DROP COLUMN device_id CASCADE"))
        conn.commit()
        # 4. 非空 + 外键 + 索引
        conn.execute(text("ALTER TABLE usage_records ALTER COLUMN device_code SET NOT NULL"))  # 已删孤儿记录
        conn.execute(text("""
            ALTER TABLE usage_records
            ADD CONSTRAINT usage_records_device_code_fkey
            FOREIGN KEY (device_code) REFERENCES devices(device_code)
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_usage_records_device_code ON usage_records(device_code)"))
    else:
        # SQLite: 无简单 ALTER 删列，需建新表、拷贝、替换（此处简化：仅删 FK 再建新表或依赖 SQLite 3.35+ 的 DROP COLUMN）
        try:
            conn.execute(text("ALTER TABLE usage_records DROP COLUMN device_id"))
        except Exception:
            print("SQLite 需手动迁移：建新表含 device_code，拷贝数据后替换。建议使用 PostgreSQL。")
            conn.rollback()
            sys.exit(1)
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_usage_records_device_code ON usage_records(device_code)"))
    conn.commit()

print("迁移完成：usage_records 已改为使用 device_code 关联设备。")