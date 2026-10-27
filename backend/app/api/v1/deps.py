"""
api/v1/deps.py — Dependencies dùng chung cho tất cả API routes
Cung cấp: get_current_user, require_giao_vien, require_quan_tri
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.nguoidung import NguoiDung, VaiTroEnum, TrangThaiTaiKhoanEnum

# Bearer token extractor
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> NguoiDung:
    """
    Dependency: Xác thực JWT và trả về NguoiDung hiện tại.
    Ném 401 nếu token không hợp lệ.
    Ném 403 nếu tài khoản bị khóa hoặc chưa được duyệt.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    ma_nguoi_dung_raw: Optional[str] = payload.get("sub")
    if ma_nguoi_dung_raw is None:
        raise credentials_exception

    try:
        ma_nguoi_dung = int(ma_nguoi_dung_raw)
    except (ValueError, TypeError):
        raise credentials_exception

    user = db.query(NguoiDung).filter(
        NguoiDung.MaNguoiDung == ma_nguoi_dung
    ).first()
    if user is None:
        raise credentials_exception

    # Kiểm tra trạng thái tài khoản
    if user.TrangThaiTaiKhoan == TrangThaiTaiKhoanEnum.CHO_DUYET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đang chờ quản trị viên phê duyệt",
        )
    if user.TrangThaiTaiKhoan == TrangThaiTaiKhoanEnum.BI_KHOA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa. Liên hệ quản trị viên.",
        )
    if user.TrangThaiTaiKhoan == TrangThaiTaiKhoanEnum.BI_TU_CHOI:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị từ chối. Vui lòng đăng ký lại.",
        )

    return user


def require_giao_vien(
    current_user: NguoiDung = Depends(get_current_user),
) -> NguoiDung:
    """
    Dependency: Chỉ cho phép GIAO_VIEN hoặc QUAN_TRI truy cập.
    Admin được phép xem/giám sát tất cả tài nguyên của giáo viên.
    """
    if current_user.VaiTro not in (VaiTroEnum.GIAO_VIEN, VaiTroEnum.QUAN_TRI):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chức năng này chỉ dành cho Giáo viên hoặc Quản trị viên",
        )
    return current_user


def require_quan_tri(
    current_user: NguoiDung = Depends(get_current_user),
) -> NguoiDung:
    """Dependency: Chỉ cho phép QUAN_TRI truy cập"""
    if current_user.VaiTro != VaiTroEnum.QUAN_TRI:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chức năng này chỉ dành cho Quản trị viên",
        )
    return current_user
