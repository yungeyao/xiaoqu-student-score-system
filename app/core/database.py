"""SQLAlchemy 引擎与会话。

默认落在 data/cj.db（SQLite），数据库地址由 core.config.DB_URL 决定，
换成 MySQL/PostgreSQL 只需改那一处。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DB_URL

# check_same_thread=False 让 SQLite 能在 FastAPI 的多线程下工作
engine = create_engine(DB_URL, connect_args={"check_same_thread": False}, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """所有模型的基类。"""


def get_db():
    """FastAPI 依赖: 每个请求一个会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
