"""
models/__init__.py
Import tất cả models để Alembic auto-detect khi generate migrations
"""
from app.models.nguoidung import NguoiDung, Quyen, NguoiDung_Quyen, NhatKyHeThong
from app.models.danhmuc import DanhMucChung
from app.models.lophoc import Lop, HocSinh
from app.models.nganhang import (
    ChuDe,
    CauHoiNganHang,
    LuaChonCauHoi,
    TuKhoa,
    CauHoiNH_TuKhoa,
    TepDinhKemCauHoi,
    LichSuChinhSuaCauHoi,
)
from app.models.dethi import DeThi, DeThi_CauHoi, MaDe, DapAnDung
from app.models.chambai import PhieuTraLoi, ChiTietBaiLam, KetQua, ThongKeCauHoi

__all__ = [
    "NguoiDung", "Quyen", "NguoiDung_Quyen", "NhatKyHeThong",
    "DanhMucChung",
    "Lop", "HocSinh",
    "ChuDe", "CauHoiNganHang", "LuaChonCauHoi", "TuKhoa",
    "CauHoiNH_TuKhoa", "TepDinhKemCauHoi", "LichSuChinhSuaCauHoi",
    "DeThi", "DeThi_CauHoi", "MaDe", "DapAnDung",
    "PhieuTraLoi", "ChiTietBaiLam", "KetQua", "ThongKeCauHoi",
]
