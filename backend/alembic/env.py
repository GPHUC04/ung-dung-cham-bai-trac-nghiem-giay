"""
alembic/env.py — Cấu hình môi trường Alembic
Đọc DATABASE_URL từ biến môi trường và import tất cả models
để Alembic có thể auto-generate migrations chính xác.
"""
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Import Base và tất cả models (PHẢI import trước khi gọi autogenerate)
from app.core.database import Base, engine, active_db_url
import app.models  # noqa — trigger __init__.py imports tất cả 22 bảng

# Lấy đối tượng cấu hình Alembic
config = context.config


# Chỉ cho phép migration lên PostgreSQL khi triển khai Supabase.
# Nếu kết nối PostgreSQL thất bại và database.py fallback sang SQLite,
# Alembic sẽ dừng thay vì chạy migration nhầm database.
if not active_db_url.startswith("postgresql"):
    raise RuntimeError(
        "Alembic yêu cầu PostgreSQL, nhưng database hiện tại "
        f"đang là: {active_db_url}"
    )

# Đọc logging config từ alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Đồng bộ URL kết nối chính xác từ active_db_url (hỗ trợ tự động fallback SQLite)
config.set_main_option("sqlalchemy.url", active_db_url)

# Metadata của tất cả models — Alembic so sánh với DB thực tế để tạo migration
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Chạy migration không cần kết nối DB (chỉ tạo SQL script)"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,   # Phát hiện thay đổi kiểu cột
        compare_server_default=True,  # Phát hiện thay đổi default value
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Chạy migration với kết nối DB thật (mặc định)"""
    connectable = engine
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
