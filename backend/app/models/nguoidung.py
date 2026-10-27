"""
models/nguoidung.py — Nhóm 1: Hệ thống / Tài khoản (4 bảng)
- NguoiDung: Tài khoản GV và Admin
- Quyen: Danh mục quyền hạn (AD-04)
- NguoiDung_Quyen: Bảng trung gian N-N gán quyền
- NhatKyHeThong: Nhật ký hành động (AD-05)

Quy ước (SQLAlchemy 2.0):
- Mapped[X]        → cột NOT NULL
- Mapped[X | None] → cột cho phép NULL
- Chỉ ghi nullable=... khi cần ghi đè quy ước trên.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Chỉ import để type checker hiểu kiểu; không import thật lúc chạy (tránh import vòng).
if TYPE_CHECKING:
    from app.models.chambai import PhieuTraLoi
    from app.models.dethi import DeThi
    from app.models.lophoc import Lop
    from app.models.nganhang import CauHoiNganHang, LichSuChinhSuaCauHoi


def _utcnow() -> datetime:
    """Giờ UTC có múi giờ, được gọi lúc INSERT (không bị chốt lúc import)."""
    return datetime.now(timezone.utc)


class VaiTroEnum(str, enum.Enum):
    GIAO_VIEN = "GIAO_VIEN"
    QUAN_TRI = "QUAN_TRI"


class TrangThaiTaiKhoanEnum(str, enum.Enum):
    CHO_DUYET = "CHO_DUYET"
    DA_KICH_HOAT = "DA_KICH_HOAT"
    BI_KHOA = "BI_KHOA"
    BI_TU_CHOI = "BI_TU_CHOI"


class NguoiDung(Base):
    """
    Tài khoản đăng nhập của Giáo viên và Quản trị hệ thống.
    Trạng thái vòng đời: CHO_DUYET → DA_KICH_HOAT ↔ BI_KHOA | BI_TU_CHOI
    """
    __tablename__ = "NguoiDung"

    MaNguoiDung: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    HoTen: Mapped[str] = mapped_column(String(100), comment="Họ tên đầy đủ")
    TenDangNhap: Mapped[str] = mapped_column(
        String(50), unique=True, comment="Tên đăng nhập duy nhất"
    )
    MatKhau_Hash: Mapped[str] = mapped_column(String(255), comment="Mật khẩu đã băm bcrypt")
    VaiTro: Mapped[VaiTroEnum] = mapped_column(
        Enum(VaiTroEnum, name="vaitro_enum"),
        comment="Phân loại: giáo viên hoặc quản trị",
    )
    TrangThaiTaiKhoan: Mapped[TrangThaiTaiKhoanEnum] = mapped_column(
        Enum(TrangThaiTaiKhoanEnum, name="trangthai_taikhoan_enum"),
        default=TrangThaiTaiKhoanEnum.CHO_DUYET,
        comment="Trạng thái vòng đời tài khoản (AD-01)",
    )
    Email: Mapped[str | None] = mapped_column(
        String(100), unique=True, comment="Email liên hệ"
    )
    NgayTao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    # Xóa user → ORM xóa luôn các dòng gán quyền (khớp ondelete=CASCADE ở DB,
    # và chạy đúng cả khi DB là SQLite chưa bật foreign_keys).
    quyen_list: Mapped[list[NguoiDung_Quyen]] = relationship(
        back_populates="nguoi_dung", cascade="all, delete-orphan"
    )
    nhat_ky: Mapped[list[NhatKyHeThong]] = relationship(back_populates="nguoi_dung")
    cau_hoi: Mapped[list[CauHoiNganHang]] = relationship(back_populates="nguoi_tao")

    lop_hoc: Mapped[list[Lop]] = relationship(back_populates="giao_vien")
    de_thi: Mapped[list[DeThi]] = relationship(back_populates="giao_vien")
    phieu_tra_loi: Mapped[list[PhieuTraLoi]] = relationship(back_populates="giao_vien_cham")
    lich_su_sua: Mapped[list[LichSuChinhSuaCauHoi]] = relationship(back_populates="nguoi_chinh_sua")

    def __repr__(self) -> str:
        return f"<NguoiDung {self.TenDangNhap} [{self.VaiTro}]>"


class Quyen(Base):
    """
    Danh mục quyền hạn chi tiết — phục vụ mở rộng khi có nhiều vai trò hơn (AD-04)
    VD: TAO_DE_THI, DUYET_CAU_HOI, XUAT_BAO_CAO
    """
    __tablename__ = "Quyen"

    MaQuyen: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    TenQuyen: Mapped[str] = mapped_column(String(100), unique=True, comment="VD: TAO_DE_THI")
    MoTa: Mapped[str | None] = mapped_column(String(255), comment="Diễn giải ý nghĩa quyền")

    nguoi_dung_list: Mapped[list[NguoiDung_Quyen]] = relationship(
        back_populates="quyen", cascade="all, delete-orphan"
    )


class NguoiDung_Quyen(Base):
    """
    Bảng trung gian N-N gán quyền cho tài khoản.
    Một tài khoản có nhiều quyền; một quyền gán cho nhiều tài khoản.
    """
    __tablename__ = "NguoiDung_Quyen"

    MaNguoiDung: Mapped[int] = mapped_column(
        Integer, ForeignKey("NguoiDung.MaNguoiDung", ondelete="CASCADE"), primary_key=True
    )
    MaQuyen: Mapped[int] = mapped_column(
        Integer, ForeignKey("Quyen.MaQuyen", ondelete="CASCADE"), primary_key=True
    )

    nguoi_dung: Mapped[NguoiDung] = relationship(back_populates="quyen_list")
    quyen: Mapped[Quyen] = relationship(back_populates="nguoi_dung_list")


class NhatKyHeThong(Base):
    """
    Nhật ký hành động quan trọng trong hệ thống (AD-05).
    Ghi lại: ai làm gì, với đối tượng nào, lúc nào.
    """
    __tablename__ = "NhatKyHeThong"

    MaNhatKy: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    # NULL khi người dùng bị xóa (ondelete=SET NULL) → giữ lại log
    MaNguoiDung: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.MaNguoiDung", ondelete="SET NULL")
    )
    HanhDong: Mapped[str] = mapped_column(
        String(100), comment="VD: PHE_DUYET_TK, DUYET_CAU_HOI, DANG_NHAP"
    )
    DoiTuongTacDong: Mapped[str | None] = mapped_column(
        String(100), comment="Đối tượng bị tác động (VD: NguoiDung#42)"
    )
    ThoiGian: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    nguoi_dung: Mapped[NguoiDung | None] = relationship(back_populates="nhat_ky") 