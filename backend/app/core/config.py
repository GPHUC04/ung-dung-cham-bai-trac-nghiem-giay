"""
core/config.py — Cấu hình ứng dụng từ biến môi trường
Sử dụng pydantic-settings để validate và load .env tự động
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, model_validator
from typing import List

_DEFAULT_SECRET_KEY = "dev-secret-key-change-this-in-production-1234567890"


class Settings(BaseSettings):
    # App info
    APP_NAME: str = "Hệ thống Chấm bài Trắc nghiệm"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/cham_bai_db"

    # Supabase
    SUPABASE_URL: str = "https://example.supabase.co"
    SUPABASE_ANON_KEY: str = "anon-key-placeholder"
    SUPABASE_SERVICE_ROLE_KEY: str = "service-role-key-placeholder"
    SUPABASE_BUCKET_PHIEU: str = "phieu-tra-loi"
    SUPABASE_BUCKET_CAUHOIANH: str = "cau-hoi-hinh-anh"

    # JWT
    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 giờ

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    @model_validator(mode="after")
    def check_production_secrets(self) -> "Settings":
        """
        Đảm bảo SECRET_KEY không phải giá trị mặc định khi chạy production.
        Sẽ raise lỗi ngay lúc khởi động nếu phát hiện cấu hình không an toàn.
        """
        if not self.DEBUG and self.SECRET_KEY == _DEFAULT_SECRET_KEY:
            raise ValueError(
                "⛔ SECRET_KEY vẫn là giá trị mặc định không an toàn! "
                "Hãy đặt SECRET_KEY trong biến môi trường trước khi chạy production. "
                "Gợi ý: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
