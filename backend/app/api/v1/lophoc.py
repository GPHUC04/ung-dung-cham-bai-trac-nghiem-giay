"""
api/v1/lophoc.py — API Quản lý Lớp học & Danh sách học sinh (GV-12)
Endpoints:
- GET  /lophoc/                    — Danh sách lớp do GV quản lý
- POST /lophoc/                    — Tạo lớp học mới
- GET  /lophoc/{ma_lop}            — Xem chi tiết lớp + danh sách học sinh
- PUT  /lophoc/{ma_lop}            — Cập nhật tên lớp / khối lớp
- DELETE /lophoc/{ma_lop}          — Xóa lớp học
- POST /lophoc/{ma_lop}/hocsinh    — Thêm 1 học sinh
- POST /lophoc/{ma_lop}/hocsinh/bulk — Import danh sách học sinh hàng loạt
- PUT  /lophoc/{ma_lop}/hocsinh/{ma_hs} — Sửa họ tên / SBD học sinh
- DELETE /lophoc/{ma_lop}/hocsinh/{ma_hs} — Xóa học sinh khỏi lớp
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.api.v1.deps import require_giao_vien
from app.models.nguoidung import NguoiDung
from app.models.lophoc import Lop, HocSinh
from app.models.danhmuc import DanhMucChung, LoaiDanhMucEnum
from app.schemas.lophoc import (
    LopCreate, LopUpdate, LopResponse, LopDetailResponse,
    HocSinhCreate, HocSinhUpdate, HocSinhResponse, HocSinhBulkCreate
)

router = APIRouter(prefix="/lophoc", tags=["Quản lý Lớp học & Học sinh"])


def _check_lop_owner(db: Session, ma_lop: int, ma_nguoi_dung: int) -> Lop:
    lop = db.query(Lop).filter(Lop.MaLop == ma_lop).first()
    if not lop:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")
    if lop.MaNguoiDung != ma_nguoi_dung:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập lớp học này.")
    return lop


@router.get("/", response_model=List[LopResponse])
def get_danh_sach_lop(
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Lấy danh sách các lớp do giáo viên hiện tại quản lý, kèm số học sinh trong lớp."""
    results = (
        db.query(Lop, func.count(HocSinh.MaHocSinh).label("SoLuongHocSinh"))
        .outerjoin(HocSinh, Lop.MaLop == HocSinh.MaLop)
        .filter(Lop.MaNguoiDung == user.MaNguoiDung)
        .group_by(Lop.MaLop)
        .all()
    )
    res = []
    for lop, count in results:
        res.append(LopResponse(
            MaLop=lop.MaLop,
            TenLop=lop.TenLop,
            MaDanhMuc=lop.MaDanhMuc,
            MaNguoiDung=lop.MaNguoiDung,
            SoLuongHocSinh=count
        ))
    return res


@router.post("/", response_model=LopResponse, status_code=status.HTTP_201_CREATED)
def create_lop(
    payload: LopCreate,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Tạo lớp học mới."""
    # Verify khối lớp
    khoi = db.query(DanhMucChung).filter(
        DanhMucChung.MaDanhMuc == payload.MaDanhMuc,
        DanhMucChung.LoaiDanhMuc == LoaiDanhMucEnum.KHOI_LOP
    ).first()
    if not khoi:
        raise HTTPException(status_code=400, detail="Khối lớp không hợp lệ.")

    lop = Lop(
        TenLop=payload.TenLop,
        MaDanhMuc=payload.MaDanhMuc,
        MaNguoiDung=user.MaNguoiDung
    )
    db.add(lop)
    db.commit()
    db.refresh(lop)

    return LopResponse(
        MaLop=lop.MaLop,
        TenLop=lop.TenLop,
        MaDanhMuc=lop.MaDanhMuc,
        MaNguoiDung=lop.MaNguoiDung,
        SoLuongHocSinh=0
    )


@router.get("/{ma_lop}", response_model=LopDetailResponse)
def get_chi_tiet_lop(
    ma_lop: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Xem thông tin chi tiết lớp học và toàn bộ danh sách học sinh."""
    lop = _check_lop_owner(db, ma_lop, user.MaNguoiDung)
    return lop


@router.put("/{ma_lop}", response_model=LopResponse)
def update_lop(
    ma_lop: int,
    payload: LopUpdate,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Cập nhật tên lớp hoặc khối lớp."""
    lop = _check_lop_owner(db, ma_lop, user.MaNguoiDung)

    if payload.TenLop:
        lop.TenLop = payload.TenLop
    if payload.MaDanhMuc:
        khoi = db.query(DanhMucChung).filter(
            DanhMucChung.MaDanhMuc == payload.MaDanhMuc,
            DanhMucChung.LoaiDanhMuc == LoaiDanhMucEnum.KHOI_LOP
        ).first()
        if not khoi:
            raise HTTPException(status_code=400, detail="Khối lớp không hợp lệ.")
        lop.MaDanhMuc = payload.MaDanhMuc

    db.commit()
    db.refresh(lop)
    count = db.query(HocSinh).filter(HocSinh.MaLop == ma_lop).count()
    return LopResponse(
        MaLop=lop.MaLop,
        TenLop=lop.TenLop,
        MaDanhMuc=lop.MaDanhMuc,
        MaNguoiDung=lop.MaNguoiDung,
        SoLuongHocSinh=count
    )


@router.delete("/{ma_lop}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lop(
    ma_lop: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Xóa lớp học và tự động xóa danh sách học sinh thuộc lớp."""
    lop = _check_lop_owner(db, ma_lop, user.MaNguoiDung)
    db.delete(lop)
    db.commit()


# --- QUẢN LÝ HỌC SINH HÀNG LOẠT & ĐƠN LẺ ---
@router.post("/{ma_lop}/hocsinh", response_model=HocSinhResponse, status_code=status.HTTP_201_CREATED)
def add_hoc_sinh(
    ma_lop: int,
    payload: HocSinhCreate,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Thêm một học sinh vào lớp (Số báo danh không trùng trong lớp)."""
    lop = _check_lop_owner(db, ma_lop, user.MaNguoiDung)

    # Check SBD collision in this class
    dup = db.query(HocSinh).filter(HocSinh.MaLop == ma_lop, HocSinh.SoBaoDanh == payload.SoBaoDanh).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"Số báo danh '{payload.SoBaoDanh}' đã tồn tại trong lớp này.")

    hs = HocSinh(
        HoTen=payload.HoTen,
        SoBaoDanh=payload.SoBaoDanh,
        MaLop=ma_lop
    )
    db.add(hs)
    db.commit()
    db.refresh(hs)
    return hs


@router.post("/{ma_lop}/hocsinh/bulk", response_model=List[HocSinhResponse], status_code=status.HTTP_201_CREATED)
def bulk_add_hoc_sinh(
    ma_lop: int,
    payload: HocSinhBulkCreate,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Import danh sách nhiều học sinh cùng lúc vào lớp."""
    lop = _check_lop_owner(db, ma_lop, user.MaNguoiDung)

    existing_sbds = {hs.SoBaoDanh for hs in db.query(HocSinh.SoBaoDanh).filter(HocSinh.MaLop == ma_lop).all()}

    new_objects = []
    added_sbds_in_batch = set()

    for item in payload.danh_sach:
        if item.SoBaoDanh in existing_sbds or item.SoBaoDanh in added_sbds_in_batch:
            raise HTTPException(
                status_code=400,
                detail=f"Trùng lặp Số báo danh '{item.SoBaoDanh}' trong danh sách học sinh."
            )
        added_sbds_in_batch.add(item.SoBaoDanh)
        new_objects.append(HocSinh(
            HoTen=item.HoTen,
            SoBaoDanh=item.SoBaoDanh,
            MaLop=ma_lop
        ))

    db.bulk_save_objects(new_objects)
    db.commit()

    return db.query(HocSinh).filter(HocSinh.MaLop == ma_lop).all()


@router.put("/{ma_lop}/hocsinh/{ma_hs}", response_model=HocSinhResponse)
def update_hoc_sinh(
    ma_lop: int,
    ma_hs: int,
    payload: HocSinhUpdate,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Cập nhật thông tin học sinh (Họ tên, SBD)."""
    _check_lop_owner(db, ma_lop, user.MaNguoiDung)
    hs = db.query(HocSinh).filter(HocSinh.MaHocSinh == ma_hs, HocSinh.MaLop == ma_lop).first()
    if not hs:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh trong lớp này.")

    if payload.SoBaoDanh and payload.SoBaoDanh != hs.SoBaoDanh:
        dup = db.query(HocSinh).filter(HocSinh.MaLop == ma_lop, HocSinh.SoBaoDanh == payload.SoBaoDanh).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Số báo danh '{payload.SoBaoDanh}' đã tồn tại.")
        hs.SoBaoDanh = payload.SoBaoDanh

    if payload.HoTen:
        hs.HoTen = payload.HoTen

    db.commit()
    db.refresh(hs)
    return hs


@router.delete("/{ma_lop}/hocsinh/{ma_hs}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hoc_sinh(
    ma_lop: int,
    ma_hs: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Xóa học sinh khỏi lớp."""
    _check_lop_owner(db, ma_lop, user.MaNguoiDung)
    hs = db.query(HocSinh).filter(HocSinh.MaHocSinh == ma_hs, HocSinh.MaLop == ma_lop).first()
    if not hs:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh trong lớp này.")
    db.delete(hs)
    db.commit()
