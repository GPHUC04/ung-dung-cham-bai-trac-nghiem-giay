"""
api/v1/danhmuc.py — API Quản lý danh mục chung & Chủ đề bài học (AD-03, GV-13)
Endpoints:
- GET  /danhmuc/             — Lấy danh sách danh mục chung (lọc theo LoaiDanhMuc)
- POST /danhmuc/             — [Admin] Tạo danh mục mới (Môn học, Khối lớp, Năm học)
- PUT  /danhmuc/{id}         — [Admin] Cập nhật danh mục
- DELETE /danhmuc/{id}       — [Admin] Xóa danh mục (ràng buộc RESTRICT)
- GET  /danhmuc/chu-de/       — Danh sách chủ đề bài học (cây phân cấp)
- POST /danhmuc/chu-de/       — Tạo chủ đề / chương / bài học mới
- DELETE /danhmuc/chu-de/{id} — Xóa chủ đề
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_quan_tri
from app.models.nguoidung import NguoiDung
from app.models.danhmuc import DanhMucChung, LoaiDanhMucEnum
from app.models.nganhang import ChuDe
from app.schemas.danhmuc import (
    DanhMucChungCreate, DanhMucChungUpdate, DanhMucChungResponse,
    ChuDeCreate, ChuDeUpdate, ChuDeResponse
)

router = APIRouter(prefix="/danhmuc", tags=["Danh mục chung & Chủ đề"])


# --- DANH MỤC CHUNG (AD-03) ---
@router.get("/", response_model=List[DanhMucChungResponse])
def get_danh_muc(
    loai: Optional[LoaiDanhMucEnum] = Query(None, description="Lọc theo MON_HOC, KHOI_LOP, NAM_HOC"),
    db: Session = Depends(get_db)
):
    query = db.query(DanhMucChung)
    if loai:
        query = query.filter(DanhMucChung.LoaiDanhMuc == loai)
    return query.all()


@router.post("/", response_model=DanhMucChungResponse, status_code=status.HTTP_201_CREATED)
def create_danh_muc(
    payload: DanhMucChungCreate,
    db: Session = Depends(get_db),
    admin: NguoiDung = Depends(require_quan_tri)
):
    existing = db.query(DanhMucChung).filter(
        DanhMucChung.LoaiDanhMuc == payload.LoaiDanhMuc,
        DanhMucChung.TenDanhMuc == payload.TenDanhMuc
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Danh mục '{payload.TenDanhMuc}' thuộc nhóm {payload.LoaiDanhMuc.value} đã tồn tại."
        )

    dm = DanhMucChung(
        LoaiDanhMuc=payload.LoaiDanhMuc,
        TenDanhMuc=payload.TenDanhMuc
    )
    db.add(dm)
    db.commit()
    db.refresh(dm)
    return dm


@router.put("/{ma_dm}", response_model=DanhMucChungResponse)
def update_danh_muc(
    ma_dm: int,
    payload: DanhMucChungUpdate,
    db: Session = Depends(get_db),
    admin: NguoiDung = Depends(require_quan_tri)
):
    dm = db.query(DanhMucChung).filter(DanhMucChung.MaDanhMuc == ma_dm).first()
    if not dm:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục.")

    if payload.TenDanhMuc:
        dm.TenDanhMuc = payload.TenDanhMuc
    db.commit()
    db.refresh(dm)
    return dm


@router.delete("/{ma_dm}", status_code=status.HTTP_204_NO_CONTENT)
def delete_danh_muc(
    ma_dm: int,
    db: Session = Depends(get_db),
    admin: NguoiDung = Depends(require_quan_tri)
):
    dm = db.query(DanhMucChung).filter(DanhMucChung.MaDanhMuc == ma_dm).first()
    if not dm:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục.")

    try:
        db.delete(dm)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa danh mục đang được gắn liền với Lớp học, Đề thi hoặc Chủ đề."
        )


# --- CHỦ ĐỀ BÀI HỌC (GV-13) ---
@router.get("/chu-de/", response_model=List[ChuDeResponse])
def get_chu_de(
    ma_mon_hoc: Optional[int] = Query(None, description="Lọc theo mã môn học (DanhMucChung)"),
    only_roots: bool = Query(False, description="Chỉ lấy các chủ đề gốc (Chương)"),
    db: Session = Depends(get_db)
):
    query = db.query(ChuDe)
    if ma_mon_hoc:
        query = query.filter(ChuDe.MaDanhMuc == ma_mon_hoc)
    if only_roots:
        query = query.filter(ChuDe.MaChuDeCha.is_(None))
    return query.all()


@router.post("/chu-de/", response_model=ChuDeResponse, status_code=status.HTTP_201_CREATED)
def create_chu_de(
    payload: ChuDeCreate,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(get_current_user)
):
    # Verify mon hoc exists
    mon = db.query(DanhMucChung).filter(
        DanhMucChung.MaDanhMuc == payload.MaDanhMuc,
        DanhMucChung.LoaiDanhMuc == LoaiDanhMucEnum.MON_HOC
    ).first()
    if not mon:
        raise HTTPException(status_code=400, detail="Mã môn học không hợp lệ.")

    if payload.MaChuDeCha:
        parent = db.query(ChuDe).filter(ChuDe.MaChuDe == payload.MaChuDeCha).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Mã chủ đề cha không tồn tại.")

    cd = ChuDe(
        TenChuDe=payload.TenChuDe,
        MaDanhMuc=payload.MaDanhMuc,
        MaChuDeCha=payload.MaChuDeCha
    )
    db.add(cd)
    db.commit()
    db.refresh(cd)
    return cd
