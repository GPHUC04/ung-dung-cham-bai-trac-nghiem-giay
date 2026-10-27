"""
schemas/dethi.py — Pydantic schemas cho Đề thi & Sinh mã đề (GV-10, GV-11)
"""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict, Field


# --- Đề thi Cốt lõi ---
class DeThiCauHoiInput(BaseModel):
    MaCauHoiNH: int
    SoThuTuGoc: int


class DeThiCreate(BaseModel):
    TenDeThi: str = Field(..., min_length=3, max_length=150, description="Tên đề thi (VD: Đề thi học kỳ I Toán 10)")
    MaDanhMuc: int = Field(..., description="Môn học (DanhMucChung.MaDanhMuc)")
    SoLuaChon: int = Field(4, ge=2, le=10, description="Số lựa chọn mỗi câu (mặc định 4: A/B/C/D)")
    danh_sach_cau_hoi: List[DeThiCauHoiInput] = Field(..., min_length=1, description="Danh sách các câu hỏi được chọn")


class SinhMaDeRequest(BaseModel):
    so_luong_ma_de: int = Field(4, ge=1, le=20, description="Số lượng mã đề cần sinh (VD: 4 mã đề: 101, 102, 103, 104)")
    tien_to_ma_de: Optional[str] = Field("10", description="Tiền tố số hiệu mã đề (VD: '10' -> 101, 102...)")
    xao_cau_hoi: bool = Field(True, description="Có xáo trộn thứ tự câu hỏi không")
    xao_dap_an: bool = Field(True, description="Có xáo trộn thứ tự phương án A/B/C/D không")


class DapAnDungResponse(BaseModel):
    MaDapAn: int
    MaDeThiCauHoi: int
    SoThuTuMoi: Optional[int] = None
    DapAnDung: str  # A/B/C/D

    model_config = ConfigDict(from_attributes=True)


class MaDeResponse(BaseModel):
    MaMaDe: int
    MaDeThi: int
    SoHieuMaDe: str
    ThuTuCauHoi_JSON: Dict[str, int]
    dap_an_dung: List[DapAnDungResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DeThiResponse(BaseModel):
    MaDeThi: int
    TenDeThi: str
    MaDanhMuc: int
    SoCau: int
    SoLuaChon: int
    MaNguoiDung: int
    NgayTao: datetime
    so_luong_ma_de: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class DeThiDetailResponse(DeThiResponse):
    ma_de_list: List[MaDeResponse] = []

    model_config = ConfigDict(from_attributes=True)
