"""
api/v1/dethi.py — API Quản lý Đề thi & Sinh mã đề hoán vị (GV-10, GV-11)
Endpoints:
- GET  /dethi/                       — Danh sách đề thi do GV tạo
- POST /dethi/                       — Tạo đề thi mới từ Ngân hàng câu hỏi
- GET  /dethi/{ma_de_thi}            — Chi tiết đề thi & danh sách mã đề
- POST /dethi/{ma_de_thi}/sinh-ma-de — Sinh N mã đề hoán vị
- GET  /dethi/{ma_de_thi}/ma-tran-dap-an — Xem ma trận đáp án đúng của tất cả mã đề
- DELETE /dethi/{ma_de_thi}          — Xóa đề thi
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import require_giao_vien
from app.models.nguoidung import NguoiDung
from app.models.dethi import DeThi, DeThi_CauHoi, MaDe, DapAnDung
from app.models.nganhang import CauHoiNganHang
from app.schemas.dethi import (
    DeThiCreate, DeThiResponse, DeThiDetailResponse,
    SinhMaDeRequest, MaDeResponse
)
from app.services.dethi import tao_danh_sach_ma_de

router = APIRouter(prefix="/dethi", tags=["Quản lý Đề thi & Mã đề"])


def _check_de_thi_owner(db: Session, ma_de_thi: int, ma_nguoi_dung: int) -> DeThi:
    dt = db.query(DeThi).filter(DeThi.MaDeThi == ma_de_thi).first()
    if not dt:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề thi.")
    if dt.MaNguoiDung != ma_nguoi_dung:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập đề thi này.")
    return dt


@router.get("/", response_model=List[DeThiResponse])
def get_danh_sach_de_thi(
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Lấy danh sách đề thi của giáo viên hiện tại."""
    de_this = db.query(DeThi).filter(DeThi.MaNguoiDung == user.MaNguoiDung).all()
    res = []
    for dt in de_this:
        so_ma_de = db.query(MaDe).filter(MaDe.MaDeThi == dt.MaDeThi).count()
        res.append(DeThiResponse.model_validate(dt).model_copy(update={"so_luong_ma_de": so_ma_de}))
    return res


@router.post("/", response_model=DeThiResponse, status_code=status.HTTP_201_CREATED)
def create_de_thi(
    payload: DeThiCreate,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Tạo đề thi gốc chọn câu hỏi từ Ngân hàng câu hỏi."""
    # Check all questions exist
    ch_ids = [ch.MaCauHoiNH for ch in payload.danh_sach_cau_hoi]
    existing_count = db.query(CauHoiNganHang).filter(CauHoiNganHang.MaCauHoiNH.in_(ch_ids)).count()
    if existing_count != len(ch_ids):
        raise HTTPException(status_code=400, detail="Một hoặc nhiều mã câu hỏi không tồn tại trong ngân hàng.")

    de_thi = DeThi(
        TenDeThi=payload.TenDeThi,
        MaDanhMuc=payload.MaDanhMuc,
        SoCau=len(payload.danh_sach_cau_hoi),
        SoLuaChon=payload.SoLuaChon,
        MaNguoiDung=user.MaNguoiDung
    )
    db.add(de_thi)
    db.flush()

    for item in payload.danh_sach_cau_hoi:
        dt_ch = DeThi_CauHoi(
            MaDeThi=de_thi.MaDeThi,
            MaCauHoiNH=item.MaCauHoiNH,
            SoThuTuGoc=item.SoThuTuGoc
        )
        db.add(dt_ch)

    db.commit()
    db.refresh(de_thi)

    return DeThiResponse.model_validate(de_thi).model_copy(update={"so_luong_ma_de": 0})


@router.get("/{ma_de_thi}", response_model=DeThiDetailResponse)
def get_chi_tiet_de_thi(
    ma_de_thi: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Chi tiết đề thi kèm danh sách mã đề."""
    dt = _check_de_thi_owner(db, ma_de_thi, user.MaNguoiDung)
    return dt


@router.post("/{ma_de_thi}/sinh-ma-de", response_model=List[MaDeResponse])
def sinh_ma_de(
    ma_de_thi: int,
    payload: SinhMaDeRequest,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Sinh ra N mã đề hoán vị ngẫu nhiên (GV-11)."""
    dt = _check_de_thi_owner(db, ma_de_thi, user.MaNguoiDung)
    ma_de_list = tao_danh_sach_ma_de(db, dt, payload)
    return ma_de_list


@router.get("/{ma_de_thi}/ma-tran-dap-an")
def get_ma_tran_dap_an(
    ma_de_thi: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
) -> Dict[str, Any]:
    """
    Trả về ma trận đáp án chuẩn để giáo viên xem/in ấn đối soát.
    Cấu trúc:
    {
      "TenDeThi": "Đề kiểm tra 1 tiết",
      "MaDeList": ["101", "102", "103", "104"],
      "Matrix": [
        {"Cau": 1, "101": "A", "102": "C", "103": "B", "104": "D"},
        ...
      ]
    }
    """
    dt = _check_de_thi_owner(db, ma_de_thi, user.MaNguoiDung)
    ma_des = db.query(MaDe).filter(MaDe.MaDeThi == ma_de_thi).all()

    ma_de_names = [m.SoHieuMaDe for m in ma_des]
    matrix_data = []

    for c_idx in range(1, dt.SoCau + 1):
        row = {"Cau": c_idx}
        for md in ma_des:
            # Tìm MaDeThiCauHoi tại vị trí c_idx (str(c_idx))
            str_idx = str(c_idx)
            dt_ch_id = md.ThuTuCauHoi_JSON.get(str_idx)
            if dt_ch_id:
                da = db.query(DapAnDung).filter(
                    DapAnDung.MaMaDe == md.MaMaDe,
                    DapAnDung.MaDeThiCauHoi == dt_ch_id
                ).first()
                row[md.SoHieuMaDe] = da.DapAnDung if da else "-"
            else:
                row[md.SoHieuMaDe] = "-"
        matrix_data.append(row)

    return {
        "MaDeThi": dt.MaDeThi,
        "TenDeThi": dt.TenDeThi,
        "MaDeList": ma_de_names,
        "Matrix": matrix_data
    }


@router.delete("/{ma_de_thi}", status_code=status.HTTP_204_NO_CONTENT)
def delete_de_thi(
    ma_de_thi: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Xóa đề thi và tất cả các mã đề sinh ra."""
    dt = _check_de_thi_owner(db, ma_de_thi, user.MaNguoiDung)
    db.delete(dt)
    db.commit()
