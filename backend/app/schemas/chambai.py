from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.chambai import TrangThaiPhieuEnum


class ChiTietBaiLamResponse(BaseModel):
    MaChiTiet: int
    MaPhieu: int
    MaDeThiCauHoi: int
    SoThuTuMoi: Optional[int] = None  # Số thứ tự trong mã đề
    DapAnDaChon: Optional[str] = None  # A/B/C/D hoặc None
    DapAnDung: Optional[str] = None    # A/B/C/D
    LaDung: Optional[bool] = None
    DoTinCay: Optional[float] = 1.0
    CoBatThuong: bool = False

    model_config = ConfigDict(from_attributes=True)


class KetQuaResponse(BaseModel):
    MaKetQua: int
    MaPhieu: int
    SoCauDung: int
    SoCauSai: int
    SoCauBoTrong: int
    Diem: float
    DaChinhSuaThuCong: bool

    model_config = ConfigDict(from_attributes=True)


class PhieuTraLoiResponse(BaseModel):
    MaPhieu: int
    MaDeThi: int
    MaHocSinh: Optional[int] = None
    TenHocSinh: Optional[str] = None
    SoBaoDanh: Optional[str] = None
    MaMaDe: Optional[int] = None
    SoHieuMaDe: Optional[str] = None
    MaLop: Optional[int] = None
    DuongDanAnhGoc: str
    ThoiGianQuet: datetime
    TrangThai: TrangThaiPhieuEnum
    ket_qua: Optional[KetQuaResponse] = None

    model_config = ConfigDict(from_attributes=True)


class PhieuTraLoiDetailResponse(PhieuTraLoiResponse):
    chi_tiet_bai_lam: List[ChiTietBaiLamResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CapNhatDapAnItem(BaseModel):
    MaDeThiCauHoi: int
    DapAnMoi: Optional[str] = Field(
        None,
        description="Đáp án mới: A, B, C hoặc D. Để trống (null) nếu muốn xóa đáp án (coi như bỏ trống)."
    )

    @field_validator("DapAnMoi")
    @classmethod
    def validate_dap_an(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().upper()
        if v not in {"A", "B", "C", "D"}:
            raise ValueError("Đáp án chỉ được là A, B, C hoặc D")
        return v


class CapNhatBaiLamRequest(BaseModel):
    """Giáo viên điều chỉnh đáp án hoặc gán lại Mã đề / Học sinh khi xem lại (GV-07)."""
    MaHocSinh: Optional[int] = None
    MaMaDe: Optional[int] = None
    dap_an_dieu_chinh: Optional[List[CapNhatDapAnItem]] = []
