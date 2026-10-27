"""
api/v1/auth.py — API xác thực người dùng (GV-01)
Endpoints:
- POST /auth/register  — Đăng ký tài khoản giáo viên
- POST /auth/login     — Đăng nhập, nhận JWT
- GET  /auth/me        — Xem thông tin bản thân
- POST /auth/logout    — Đăng xuất (client-side, invalidate bằng token blacklist nếu cần)
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.nguoidung import NguoiDung, VaiTroEnum, TrangThaiTaiKhoanEnum, NhatKyHeThong
from app.schemas.auth import (
    DangKyRequest, DangNhapRequest,
    TokenResponse, NguoiDungPublic, MessageResponse,
)
from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["🔐 Xác thực"])


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản giáo viên",
    description="Tạo tài khoản mới với trạng thái CHO_DUYET. Admin sẽ phê duyệt sau.",
)
def dang_ky(request: DangKyRequest, db: Session = Depends(get_db)):
    # Kiểm tra tên đăng nhập đã tồn tại chưa
    existing = db.query(NguoiDung).filter(
        NguoiDung.TenDangNhap == request.ten_dang_nhap
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tên đăng nhập '{request.ten_dang_nhap}' đã được sử dụng",
        )

    # Kiểm tra email nếu có
    if request.email:
        existing_email = db.query(NguoiDung).filter(
            NguoiDung.Email == request.email
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email này đã được đăng ký",
            )

    # Tạo tài khoản mới
    new_user = NguoiDung(
        HoTen=request.ho_ten.strip(),
        TenDangNhap=request.ten_dang_nhap,
        MatKhau_Hash=hash_password(request.mat_khau),
        VaiTro=VaiTroEnum.GIAO_VIEN,
        TrangThaiTaiKhoan=TrangThaiTaiKhoanEnum.CHO_DUYET,
        Email=request.email,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Ghi nhật ký
    log = NhatKyHeThong(
        MaNguoiDung=new_user.MaNguoiDung,
        HanhDong="DANG_KY_TAI_KHOAN",
        DoiTuongTacDong=f"NguoiDung#{new_user.MaNguoiDung}",
    )
    db.add(log)
    db.commit()

    return MessageResponse(
        message=f"Đăng ký thành công! Tài khoản '{request.ten_dang_nhap}' đang chờ quản trị viên phê duyệt.",
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập",
    description="Đăng nhập bằng tên đăng nhập + mật khẩu, nhận JWT access token.",
)
def dang_nhap(request: DangNhapRequest, db: Session = Depends(get_db)):
    # Tìm user theo tên đăng nhập
    user = db.query(NguoiDung).filter(
        NguoiDung.TenDangNhap == request.ten_dang_nhap.lower().strip()
    ).first()

    # Sai tên đăng nhập hoặc mật khẩu (cùng thông báo để tránh enumeration)
    if not user or not verify_password(request.mat_khau, user.MatKhau_Hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Kiểm tra trạng thái
    if user.TrangThaiTaiKhoan == TrangThaiTaiKhoanEnum.CHO_DUYET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đang chờ quản trị viên phê duyệt. Vui lòng chờ.",
        )
    if user.TrangThaiTaiKhoan == TrangThaiTaiKhoanEnum.BI_KHOA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa. Liên hệ quản trị viên để được hỗ trợ.",
        )
    if user.TrangThaiTaiKhoan == TrangThaiTaiKhoanEnum.BI_TU_CHOI:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị từ chối đăng ký. Vui lòng liên hệ quản trị viên.",
        )

    # Tạo JWT
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": str(user.MaNguoiDung), "role": user.VaiTro.value},
        expires_delta=expires,
    )

    # Ghi nhật ký đăng nhập
    log = NhatKyHeThong(
        MaNguoiDung=user.MaNguoiDung,
        HanhDong="DANG_NHAP",
        DoiTuongTacDong=f"NguoiDung#{user.MaNguoiDung}",
    )
    db.add(log)
    db.commit()

    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        nguoi_dung=NguoiDungPublic.model_validate(user),
    )


@router.get(
    "/me",
    response_model=NguoiDungPublic,
    summary="Thông tin tài khoản hiện tại",
)
def lay_thong_tin_ban_than(
    current_user: NguoiDung = Depends(get_current_user),
):
    """Trả về thông tin tài khoản của người đang đăng nhập."""
    return NguoiDungPublic.model_validate(current_user)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Đăng xuất",
    description="Client xóa token khỏi bộ nhớ. Server ghi nhật ký.",
)
def dang_xuat(
    current_user: NguoiDung = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = NhatKyHeThong(
        MaNguoiDung=current_user.MaNguoiDung,
        HanhDong="DANG_XUAT",
        DoiTuongTacDong=f"NguoiDung#{current_user.MaNguoiDung}",
    )
    db.add(log)
    db.commit()
    return MessageResponse(message="Đăng xuất thành công")
