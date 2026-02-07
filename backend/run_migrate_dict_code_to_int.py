"""
将字典编码从英文改为数字：dict_items.code 改为整数，并迁移 usage_records、devices 中的旧值。
仅需在已有数据库上执行一次。新库由 create_all + 种子数据即可。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from database import engine
from models import Base, DictItem

_USAGE_MAP = {"routine": "1", "borrow": "2", "maintenance": "3", "calibration": "4", "other": "5"}
_STATUS_MAP = {"available": "1", "in_use": "2", "maintenance": "3", "fault": "4", "scrapped": "5"}


def migrate():
    with engine.connect() as conn:
        # 检查 dict_items 是否仍为旧结构（code 为字符串类型）
        try:
            r = conn.execute(text("SELECT code FROM dict_items LIMIT 1"))
            row = r.fetchone()
            if row is None:
                conn.commit()
                return  # 表空，由应用种子即可
            # 若 code 已是数字则无需迁移
            try:
                int(row[0])
                print("dict_items.code 已是数字，跳过迁移")
                conn.commit()
                return
            except (ValueError, TypeError):
                pass
        except Exception:
            conn.rollback()
            print("dict_items 表不存在或结构不同，跳过字典迁移")
            return

        # 迁移 usage_records.usage_type
        for eng, num in _USAGE_MAP.items():
            conn.execute(
                text("UPDATE usage_records SET usage_type = :num WHERE usage_type = :eng"),
                {"num": num, "eng": eng},
            )
        # 迁移 devices.status
        for eng, num in _STATUS_MAP.items():
            conn.execute(
                text("UPDATE devices SET status = :num WHERE status = :eng"),
                {"num": num, "eng": eng},
            )

        # 重建 dict_items：SQLite 无法直接改列类型，故删表后由 create_all 重建并种子
        conn.execute(text("DROP TABLE IF EXISTS dict_items"))
        conn.commit()

    Base.metadata.create_all(bind=engine)

    from database import SessionLocal
    db = SessionLocal()
    try:
        for item in [
            ("usage_type", 1, "常规使用", 1),
            ("usage_type", 2, "借用", 2),
            ("usage_type", 3, "维修/故障", 3),
            ("usage_type", 4, "校准/质控", 4),
            ("usage_type", 5, "其他", 5),
            ("device_status", 1, "可用", 1),
            ("device_status", 2, "使用中", 2),
            ("device_status", 3, "维修中", 3),
            ("device_status", 4, "故障", 4),
            ("device_status", 5, "报废", 5),
        ]:
            db.add(DictItem(dict_type=item[0], code=str(item[1]), label=item[2], sort_order=item[3]))
        db.commit()
        print("字典编码已迁移为数字，并已重写 dict_items 种子数据。")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
