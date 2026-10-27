"""
schemas/lophoc.py — Pydantic schemas cho Lớp học & Học sinh (GV-12)
"""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# --- Học Sinh Schemas ---
class HocSinhBase(BaseModel):
    HoTen: str = Field(..., min_length=2, max_length=100, description="Họ tên học sinh")
    SoBaoDanh: str = Field(..., min_length=1, max_length=20, description="Số báo danh (duy nhất trong lớp)")


class HocSinhCreate(HocSinhBase):
    pass


class HocSinhUpdate(BaseModel):
    HoTen: Optional[str] = None
    SoBaoDanh: Optional[str] = None


class HocSinhBulkCreate(BaseModel):
    danh_sach: List[HocSinhCreate]


class HocSinhResponse(HocSinhBase):
    MaHocSinh: int
    MaLop: int

    model_config = ConfigDict(from_attributes=True)


# --- Lớp Học Schemas ---
class LopBase(BaseModel):
    TenLop: str = Field(..., min_length=1, max_length=50, description="Tên lớp, VD: 10A1")
    MaDanhMuc: int = Field(..., description="Mã khối lớp (DanhMucChung.MaDanhMuc)")


class LopCreate(LopBase):
    pass


class LopUpdate(BaseModel):
    TenLop: Optional[str] = None
    MaDanhMuc: Optional[int] = None


class LopResponse(LopBase):
    MaLop: int
    MaNguoiDung: int
    SoLuongHocSinh: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class LopDetailResponse(LopResponse):
    hoc_sinh: List[HocSinhResponse] = []

    model_config = ConfigDict(from_attributes=True)
