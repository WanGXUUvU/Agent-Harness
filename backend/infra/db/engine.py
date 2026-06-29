"""创建数据库引擎和会话工厂。"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# ── 连接配置 ──────────────────────────────────────────────────────────────────

DATABASE_URL = "sqlite:///./agent_session.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # 锁被占用时等待最多 30 秒
    },
)


# WAL 模式：允许并发读写，多线程下不互相阻塞
@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_conn, _connection_record):
    """为数据库连接开启 WAL 模式。"""
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute(
        "PRAGMA synchronous=NORMAL"
    )  # WAL 下 NORMAL 已足够安全，写入更快


# ── ORM 基类 & 会话工厂 ───────────────────────────────────────────────────────

SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    bind=engine,
)

Base = declarative_base()


# ── 依赖注入入口 ──────────────────────────────────────────────────────────────


def get_db():
    """提供请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
