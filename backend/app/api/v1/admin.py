"""
api/v1/admin.py — API quản trị hệ thống (AD-01 đến AD-05)
Endpoints:
- GET  /admin/tai-khoan          — Danh sách tài khoản (lọc theo trạng thái)
- POST /admin/tai-khoan/{id}/phe-duyet  — Phê duyệt tài khoản
- POST /admin/tai-khoan/{id}/tu-choi   — Từ chối tài khoản
- POST /admin/tai-khoan/{id}/khoa      — Khóa tài khoản
- POST /admin/tai-khoan/{id}/mo-khoa   — Mở khóa tài khoản
- GET  /admin/nhat-ky            — Xem nhật ký hệ thống (AD-05)
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.nguoidung import (
    NguoiDung, NhatKyHeThong,
    TrangThaiTaiKhoanEnum, VaiTroEnum
)
from app.schemas.auth import NguoiDungPublic, MessageResponse
from app.api.v1.deps import require_quan_tri

router = APIRouter(prefix="/admin", tags=["👑 Quản trị"])


class NhatKyPublic(BaseModel):
    MaNhatKy: int
    MaNguoiDung: Optional[int]
    HanhDong: str
    DoiTuongTacDong: Optional[str]
    ThoiGian: datetime

    model_config = ConfigDict(from_attributes=True)


def _ghi_nhat_ky(db: Session, ma_nguoi_dung: int, hanh_dong: str, doi_tuong: str):
    """Helper ghi nhật ký hệ thống"""
    log = NhatKyHeThong(
        MaNguoiDung=ma_nguoi_dung,
        HanhDong=hanh_dong,
        DoiTuongTacDong=doi_tuong,
    )
    db.add(log)


@router.get(
    "/tai-khoan",
    response_model=List[NguoiDungPublic],
    summary="Danh sách tài khoản giáo viên (AD-01)",
)
def lay_danh_sach_tai_khoan(
    trang_thai: Optional[TrangThaiTaiKhoanEnum] = Query(
        None, description="Lọc theo trạng thái: CHO_DUYET, DA_KICH_HOAT, BI_KHOA, BI_TU_CHOI"
    ),
    current_admin: NguoiDung = Depends(require_quan_tri),
    db: Session = Depends(get_db),
):
    query = db.query(NguoiDung).filter(NguoiDung.VaiTro == VaiTroEnum.GIAO_VIEN)
    if trang_thai:
        query = query.filter(NguoiDung.TrangThaiTaiKhoan == trang_thai)
    return [NguoiDungPublic.model_validate(u) for u in query.all()]


def _doi_trang_thai(
    ma_nguoi_dung: int,
    trang_thai_moi: TrangThaiTaiKhoanEnum,
    hanh_dong: str,
    current_admin: NguoiDung,
    db: Session,
    thong_bao: str,
) -> MessageResponse:
    """Helper chung cho các thao tác thay đổi trạng thái tài khoản"""
    user = db.query(NguoiDung).filter(NguoiDung.MaNguoiDung == ma_nguoi_dung).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    if user.VaiTro == VaiTroEnum.QUAN_TRI:
        raise HTTPException(status_code=400, detail="Không thể thay đổi trạng thái tài khoản admin")

    user.TrangThaiTaiKhoan = trang_thai_moi
    _ghi_nhat_ky(db, current_admin.MaNguoiDung, hanh_dong, f"NguoiDung#{ma_nguoi_dung}")
    db.commit()
    return MessageResponse(message=thong_bao)


@router.post(
    "/tai-khoan/{ma_nguoi_dung}/phe-duyet",
    response_model=MessageResponse,
    summary="Phê duyệt tài khoản giáo viên (AD-01)",
)
def phe_duyet_tai_khoan(
    ma_nguoi_dung: int,
    current_admin: NguoiDung = Depends(require_quan_tri),
    db: Session = Depends(get_db),
):
    return _doi_trang_thai(
        ma_nguoi_dung, TrangThaiTaiKhoanEnum.DA_KICH_HOAT,
        "PHE_DUYET_TAI_KHOAN", current_admin, db,
        "Tài khoản đã được phê duyệt. Giáo viên có thể đăng nhập."
    )


@router.post(
    "/tai-khoan/{ma_nguoi_dung}/tu-choi",
    response_model=MessageResponse,
    summary="Từ chối đăng ký tài khoản (AD-01)",
)
def tu_choi_tai_khoan(
    ma_nguoi_dung: int,
    current_admin: NguoiDung = Depends(require_quan_tri),
    db: Session = Depends(get_db),
):
    return _doi_trang_thai(
        ma_nguoi_dung, TrangThaiTaiKhoanEnum.BI_TU_CHOI,
        "TU_CHOI_TAI_KHOAN", current_admin, db,
        "Đã từ chối đăng ký tài khoản."
    )


@router.post(
    "/tai-khoan/{ma_nguoi_dung}/khoa",
    response_model=MessageResponse,
    summary="Khóa tài khoản đang hoạt động (AD-01)",
)
def khoa_tai_khoan(
    ma_nguoi_dung: int,
    current_admin: NguoiDung = Depends(require_quan_tri),
    db: Session = Depends(get_db),
):
    # Lưu ý: token hiện tại của user sẽ bị từ chối ở deps.get_current_user khi họ gọi API tiếp theo
    return _doi_trang_thai(
        ma_nguoi_dung, TrangThaiTaiKhoanEnum.BI_KHOA,
        "KHOA_TAI_KHOAN", current_admin, db,
        "Tài khoản đã bị khóa. Mọi phiên đăng nhập sẽ bị từ chối ở lần gọi API tiếp theo."
    )


@router.post(
    "/tai-khoan/{ma_nguoi_dung}/mo-khoa",
    response_model=MessageResponse,
    summary="Mở khóa tài khoản (AD-01)",
)
def mo_khoa_tai_khoan(
    ma_nguoi_dung: int,
    current_admin: NguoiDung = Depends(require_quan_tri),
    db: Session = Depends(get_db),
):
    return _doi_trang_thai(
        ma_nguoi_dung, TrangThaiTaiKhoanEnum.DA_KICH_HOAT,
        "MO_KHOA_TAI_KHOAN", current_admin, db,
        "Tài khoản đã được mở khóa."
    )


@router.get(
    "/nhat-ky",
    response_model=List[NhatKyPublic],
    summary="Xem nhật ký hệ thống (AD-05)",
)
def xem_nhat_ky(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    hanh_dong: Optional[str] = Query(None, description="Lọc theo loại hành động"),
    current_admin: NguoiDung = Depends(require_quan_tri),
    db: Session = Depends(get_db),
):
    query = db.query(NhatKyHeThong).order_by(NhatKyHeThong.ThoiGian.desc())
    if hanh_dong:
        query = query.filter(NhatKyHeThong.HanhDong.ilike(f"%{hanh_dong}%"))
    logs = query.offset(skip).limit(limit).all()
    return [NhatKyPublic.model_validate(log) for log in logs]
