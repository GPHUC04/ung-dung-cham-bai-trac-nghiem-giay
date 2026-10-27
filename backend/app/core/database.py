# import logging
# from sqlalchemy import create_engine, text
# from sqlalchemy.orm import declarative_base, sessionmaker
# from app.core.config import settings
# from sqlalchemy.orm import DeclarativeBase, sessionmaker   # bỏ declarative_base

# # Base class cho tất cả ORM models (từ SQLAlchemy 2.0)
# class Base(DeclarativeBase):
#     pass



import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass

logger = logging.getLogger("uvicorn.error")

def get_engine(db_url: str):
    """
    Tạo SQLAlchemy engine với tham số phù hợp theo Dialect (PostgreSQL hoặc SQLite)
    """
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG,
        )
    else:
        return create_engine(
            db_url,
            connect_args={"connect_timeout": 3},
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=settings.DEBUG,
        )

# Thử kết nối DATABASE_URL ban đầu, nếu PostgreSQL không khả dụng thì fallback sang SQLite local
active_db_url = settings.DATABASE_URL
try:
    engine = get_engine(active_db_url)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as exc:
    logger.warning(
        f"Không thể kết nối tới PostgreSQL database ({active_db_url}): {exc}."
    )
    logger.warning("Tự động chuyển sang cơ sở dữ liệu SQLite local (sqlite:///./cham_bai.db)...")
    active_db_url = "sqlite:///./cham_bai.db"
    engine = get_engine(active_db_url)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho tất cả ORM models
# Base = declarative_base()

# Lưu ý: create_all() được gọi trong lifespan() của main.py,
# sau khi tất cả models đã được import. Không gọi ở đây để tránh circular import.



def get_db():
    """
    Dependency injection cho FastAPI.
    Mỗi request sẽ nhận 1 session riêng, tự đóng sau khi xong.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

