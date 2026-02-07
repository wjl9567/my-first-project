"""为 devices 表增加 is_deleted 列（软删除），若已存在则跳过。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from database import engine


def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT is_deleted FROM devices LIMIT 1"))
            conn.rollback()
            print("devices.is_deleted 已存在，跳过")
            return
        except Exception:
            conn.rollback()
        # SQLite / PostgreSQL 兼容：添加列
        try:
            conn.execute(text("ALTER TABLE devices ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
            conn.commit()
            print("已添加 devices.is_deleted")
        except Exception as e:
            conn.rollback()
            # PostgreSQL 用 FALSE
            try:
                conn.execute(text("ALTER TABLE devices ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print("已添加 devices.is_deleted")
            except Exception as e2:
                conn.rollback()
                print("迁移失败:", e2)


if __name__ == "__main__":
    migrate()
