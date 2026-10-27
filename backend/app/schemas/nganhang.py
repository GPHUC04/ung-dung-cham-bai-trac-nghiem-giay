"""
schemas/nganhang.py — Pydantic schemas cho Ngân hàng câu hỏi (GV-13, AD-02)
Hỗ trợ:
- Đáp án A/B/C/D (LuaChonCauHoi)
- Mức độ nhận thức (Bloom)
- Trạng thái kiểm duyệt (NHAP, CHO_DUYET, DA_DUYET, TU_CHOI)
- Từ khóa (tags) & tệp đính kèm (ảnh minh họa)
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.nganhang import MucDoNhanThucEnum, TrangThaiDuyetEnum, LoaiTepEnum


# --- Options (LuaChonCauHoi) ---
class LuaChonCreate(BaseModel):
    NoiDungLuaChon: str = Field(..., description="Nội dung phương án chọn")
    LaDapAnDung: bool = Field(False, description="Đánh dấu đáp án đúng")
    ThuTuHienThi: int = Field(..., ge=1, le=10, description="Thứ tự 1=A, 2=B, 3=C, 4=D")


class LuaChonResponse(LuaChonCreate):
    MaLuaChon: int
    MaCauHoiNH: int

    model_config = ConfigDict(from_attributes=True)


# --- Attachments (TepDinhKem) ---
class TepDinhKemCreate(BaseModel):
    DuongDan: str
    LoaiTep: LoaiTepEnum = LoaiTepEnum.HINH_ANH


class TepDinhKemResponse(TepDinhKemCreate):
    MaTepDinhKem: int
    MaCauHoiNH: int

    model_config = ConfigDict(from_attributes=True)


# --- Tags (TuKhoa) ---
class TuKhoaResponse(BaseModel):
    MaTuKhoa: int
    TenTuKhoa: str

    model_config = ConfigDict(from_attributes=True)


# --- Main Question Schemas (CauHoiNganHang) ---
class CauHoiCreate(BaseModel):
    NoiDungCauHoi: str = Field(..., min_length=5, description="Toàn văn nội dung câu hỏi")
    MaChuDe: int = Field(..., description="Mã chủ đề / bài học")
    MucDoNhanThuc: MucDoNhanThucEnum = Field(MucDoNhanThucEnum.NHAN_BIET, description="Nhận biết, Thông hiểu, Vận dụng, Vận dụng cao")
    lua_chon: List[LuaChonCreate] = Field(..., min_length=2, description="Danh sách phương án lựa chọn")
    tu_khoa: Optional[List[str]] = Field(default=[], description="Danh sách tên từ khóa (tags)")
    tep_dinh_kem: Optional[List[TepDinhKemCreate]] = Field(default=[], description="Ảnh/tệp đính kèm")


class CauHoiUpdate(BaseModel):
    NoiDungCauHoi: Optional[str] = None
    MaChuDe: Optional[int] = None
    MucDoNhanThuc: Optional[MucDoNhanThucEnum] = None
    lua_chon: Optional[List[LuaChonCreate]] = None
    tu_khoa: Optional[List[str]] = None
    TrangThaiDuyet: Optional[TrangThaiDuyetEnum] = None


class CauHoiDuyetRequest(BaseModel):
    TrangThaiDuyet: TrangThaiDuyetEnum  # DA_DUYET hoặc TU_CHOI
    LyDoTuChoi: Optional[str] = None


class CauHoiResponse(BaseModel):
    MaCauHoiNH: int
    NoiDungCauHoi: str
    MaChuDe: int
    MucDoNhanThuc: MucDoNhanThucEnum
    TrangThaiDuyet: TrangThaiDuyetEnum
    MaNguoiDung: int
    SoLanSuDung: int
    NgayTao: datetime
    NgayCapNhat: Optional[datetime] = None

    lua_chon: List[LuaChonResponse] = []
    tep_dinh_kem: List[TepDinhKemResponse] = []

    model_config = ConfigDict(from_attributes=True)
