"""
api/v1/thongke.py — API Báo cáo & Thống kê điểm số (GV-09, AD-07)
Endpoints:
- GET /thongke/dethi/{ma_de_thi}/lop     — Thống kê phổ điểm & tỉ lệ học lực theo lớp
- GET /thongke/dethi/{ma_de_thi}/cau-hoi — Thống kê phân tích độ khó từng câu hỏi
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import require_giao_vien
from app.models.nguoidung import NguoiDung
from app.schemas.thongke import ThongKeLopResponse, ThongKeCauHoiItem
from app.services.thongke import tinh_thong_ke_lop, tinh_thong_ke_cau_hoi

from fastapi.responses import StreamingResponse, Response
from app.services.export import export_bang_diem_excel, export_bang_diem_csv

router = APIRouter(prefix="/thongke", tags=["Thống kê & Báo cáo"])


@router.get("/dethi/{ma_de_thi}/lop", response_model=ThongKeLopResponse)
def get_thong_ke_lop(
    ma_de_thi: int,
    ma_lop: Optional[int] = Query(None, description="Lọc theo mã lớp học cụ thể"),
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Lấy báo cáo thống kê phổ điểm, điểm trung bình và phân loại học lực."""
    try:
        res = tinh_thong_ke_lop(db, ma_de_thi, ma_lop)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dethi/{ma_de_thi}/cau-hoi", response_model=List[ThongKeCauHoiItem])
def get_thong_ke_cau_hoi(
    ma_de_thi: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Phân tích độ khó thực tế và tỉ lệ chọn từng phương án A/B/C/D cho các câu hỏi trong đề thi."""
    res = tinh_thong_ke_cau_hoi(db, ma_de_thi)
    return res


@router.get("/dethi/{ma_de_thi}/export/excel")
def export_excel(
    ma_de_thi: int,
    ma_lop: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Tải tệp Excel bảng điểm chi tiết (.xlsx)."""
    stream, filename = export_bang_diem_excel(db, ma_de_thi, ma_lop)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/dethi/{ma_de_thi}/export/csv")
def export_csv(
    ma_de_thi: int,
    ma_lop: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Tải tệp CSV bảng điểm chi tiết (.csv)."""
    csv_str, filename = export_bang_diem_csv(db, ma_de_thi, ma_lop)
    return Response(
        content=csv_str.encode("utf-8-sig"),  # UTF-8 BOM cho Excel mở tiếng Việt không lỗi font
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

