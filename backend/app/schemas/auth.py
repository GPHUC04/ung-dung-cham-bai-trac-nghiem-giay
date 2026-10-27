"""
schemas/auth.py — Pydantic schemas cho Authentication (GV-01)
Validate dữ liệu đầu vào/ra của các API đăng ký, đăng nhập.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator, ConfigDict
from app.models.nguoidung import VaiTroEnum, TrangThaiTaiKhoanEnum


# ── Request schemas (Client → Server) ──────────────────────────────────────

class DangKyRequest(BaseModel):
    """
    Đăng ký tài khoản giáo viên mới (GV-01).
    Trạng thái sau khi đăng ký: CHO_DUYET (admin chưa phê duyệt).
    """
    ho_ten: str
    ten_dang_nhap: str
    mat_khau: str
    mat_khau_xac_nhan: str
    email: Optional[EmailStr] = None

    @field_validator("ten_dang_nhap")
    @classmethod
    def validate_ten_dang_nhap(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Tên đăng nhập phải có ít nhất 3 ký tự")
        if not v.replace("_", "").replace(".", "").isalnum():
            raise ValueError("Tên đăng nhập chỉ được chứa chữ, số, dấu _ và .")
        return v.lower()

    @field_validator("mat_khau")
    @classmethod
    def validate_mat_khau(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Mật khẩu phải có ít nhất 6 ký tự")
        return v

    @model_validator(mode="after")
    def check_mat_khau_khop(self) -> "DangKyRequest":
        if self.mat_khau != self.mat_khau_xac_nhan:
            raise ValueError("Mật khẩu xác nhận không khớp")
        return self


class DangNhapRequest(BaseModel):
    """Đăng nhập bằng tên đăng nhập + mật khẩu"""
    ten_dang_nhap: str
    mat_khau: str


# ── Response schemas (Server → Client) ─────────────────────────────────────

class NguoiDungPublic(BaseModel):
    """Thông tin người dùng trả về (không có mật khẩu)"""
    MaNguoiDung: int
    HoTen: str
    TenDangNhap: str
    VaiTro: VaiTroEnum
    TrangThaiTaiKhoan: TrangThaiTaiKhoanEnum
    Email: Optional[str] = None
    NgayTao: datetime

    model_config = ConfigDict(from_attributes=True)  # Đọc từ SQLAlchemy ORM object


class TokenResponse(BaseModel):
    """Response khi đăng nhập thành công"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int          # Giây
    nguoi_dung: NguoiDungPublic


class MessageResponse(BaseModel):
    """Response đơn giản chỉ có thông báo"""
    message: str
    success: bool = True
