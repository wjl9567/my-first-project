"""初始化字典表数据：使用类型、设备状态。首次部署或表为空时运行。"""
import os
import sys

# 确保 backend 在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from models import Base, DictItem
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def seed_dict():
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        if db.query(DictItem).first() is not None:
            print("dict_items 已有数据，跳过初始化")
            return
        items = [
            # 使用类型
            DictItem(dict_type="usage_type", code="routine", label="常规使用", sort_order=1),
            DictItem(dict_type="usage_type", code="borrow", label="借用", sort_order=2),
            DictItem(dict_type="usage_type", code="maintenance", label="维修/故障", sort_order=3),
            DictItem(dict_type="usage_type", code="calibration", label="校准/质控", sort_order=4),
            DictItem(dict_type="usage_type", code="other", label="其他", sort_order=5),
            # 设备状态
            DictItem(dict_type="device_status", code="available", label="可用", sort_order=1),
            DictItem(dict_type="device_status", code="in_use", label="使用中", sort_order=2),
            DictItem(dict_type="device_status", code="maintenance", label="维修中", sort_order=3),
            DictItem(dict_type="device_status", code="fault", label="故障", sort_order=4),
            DictItem(dict_type="device_status", code="scrapped", label="报废", sort_order=5),
        ]
        for i in items:
            db.add(i)
        db.commit()
        print("字典表初始化完成，共 %d 条" % len(items))
    finally:
        db.close()


if __name__ == "__main__":
    seed_dict()
