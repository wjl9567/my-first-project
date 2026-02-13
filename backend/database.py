import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from dotenv import load_dotenv


class Base(DeclarativeBase):
    pass


@lru_cache
def get_database_url() -> str:
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        # 默认本地开发数据库
        url = "postgresql+psycopg2://user:password@localhost:5432/device_scan"
    return url


engine = create_engine(
    get_database_url(),
    echo=False,
    future=True,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    from sqlalchemy.orm import Session

    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

