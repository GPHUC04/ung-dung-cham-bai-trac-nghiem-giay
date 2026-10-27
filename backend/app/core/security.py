"""
core/security.py — Xác thực JWT và mã hóa mật khẩu bcrypt
"""
import bcrypt
from datetime import datetime, timedelta, timezone
from collections.abc import Mapping
from typing import Any, Optional

from jose import JWTError, jwt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    """Băm mật khẩu bằng bcrypt trước khi lưu vào DB"""
    # Truncate password to 72 bytes if needed per bcrypt spec
    password_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """So khớp mật khẩu nhập vào với hash đã lưu"""
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Tạo JWT access token.

    Args:
        data: Payload cần mã hóa (thường chứa sub=MaNguoiDung, role=VaiTro)
        expires_delta: Thời gian hiệu lực (mặc định lấy từ settings)

    Returns:
        Chuỗi JWT đã ký
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Mapping[str, Any] | None:
    """
    Giải mã JWT và trả về payload.
    Trả về None nếu token không hợp lệ hoặc đã hết hạn.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
