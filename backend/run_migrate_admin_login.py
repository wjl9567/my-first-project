"""一次性脚本：为 users 表添加 username、password_hash，wx_userid 改为可空。执行后可直接删除本文件。"""
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
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(64) UNIQUE"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"))
    conn.execute(text("ALTER TABLE users ALTER COLUMN wx_userid DROP NOT NULL"))
    conn.commit()
print("迁移完成：users 表已添加 username、password_hash，wx_userid 已改为可空。")
