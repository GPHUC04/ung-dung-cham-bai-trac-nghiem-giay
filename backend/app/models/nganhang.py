
"""
models/nganhang.py — Nhóm 2: Ngân hàng câu hỏi

Các model:
1. ChuDe
2. CauHoiNganHang
3. LuaChonCauHoi
4. TuKhoa
5. CauHoiNH_TuKhoa
6. TepDinhKemCauHoi
7. LichSuChinhSuaCauHoi

Sử dụng SQLAlchemy 2.0:
- Mapped
- mapped_column
- Declarative Base dùng chung từ database.py
- Relationship có kiểu dữ liệu
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base



if TYPE_CHECKING:
    from app.models.danhmuc import DanhMucChung
    from app.models.nguoidung import NguoiDung
    from app.models.dethi import DeThi_CauHoi


def _utcnow() -> datetime:
    """Lấy thời điểm UTC."""
    return datetime.now(timezone.utc)


class MucDoNhanThucEnum(str, PyEnum):
    NHAN_BIET = "NHAN_BIET"
    THONG_HIEU = "THONG_HIEU"
    VAN_DUNG = "VAN_DUNG"
    VAN_DUNG_CAO = "VAN_DUNG_CAO"


class TrangThaiDuyetEnum(str, PyEnum):
    NHAP = "NHAP"
    CHO_DUYET = "CHO_DUYET"
    DA_DUYET = "DA_DUYET"
    TU_CHOI = "TU_CHOI"


class LoaiTepEnum(str, PyEnum):
    HINH_ANH = "HINH_ANH"
    CONG_THUC = "CONG_THUC"
    KHAC = "KHAC"





class ChuDe(Base):
    __tablename__ = "ChuDe"

    MaChuDe: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    TenChuDe: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    MoTa: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    MaChuDeCha: Mapped[int | None] = mapped_column(
        ForeignKey("ChuDe.MaChuDe", ondelete="SET NULL"),
        nullable=True,
    )

    MaDanhMuc: Mapped[int] = mapped_column(
        ForeignKey("DanhMucChung.MaDanhMuc", ondelete="RESTRICT"),
        nullable=False,
    )

    # Quan hệ tự tham chiếu: chủ đề cha - chủ đề con
    chu_de_cha: Mapped[ChuDe | None] = relationship(
        "ChuDe",
        remote_side="ChuDe.MaChuDe",
        back_populates="chu_de_con",
    )

    chu_de_con: Mapped[list[ChuDe]] = relationship(
        "ChuDe",
        back_populates="chu_de_cha",
    )

    # Danh mục môn học
    mon_hoc: Mapped[DanhMucChung] = relationship(
        "DanhMucChung",
        back_populates="chu_de",
    )

    # Các câu hỏi thuộc chủ đề
    cau_hoi: Mapped[list[CauHoiNganHang]] = relationship(
        "CauHoiNganHang",
        back_populates="chu_de",
    )


class CauHoiNganHang(Base):
    """
    Câu hỏi trong ngân hàng.

    Quy tắc nghiệp vụ:
    Nếu câu hỏi đã được sử dụng trong phiếu trả lời thuộc
    bài thi đã chốt, không sửa trực tiếp câu hỏi hoặc đáp án.
    Cần tạo phiên bản/câu hỏi mới và lưu nội dung cũ vào
    LichSuChinhSuaCauHoi theo quy trình nghiệp vụ.
    """

    __tablename__ = "CauHoiNganHang"

    MaCauHoiNH: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    NoiDung: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    MaChuDe: Mapped[int] = mapped_column(
        ForeignKey("ChuDe.MaChuDe", ondelete="RESTRICT"),
        nullable=False,
    )

    MucDoNhanThuc: Mapped[MucDoNhanThucEnum] = mapped_column(
        SAEnum(MucDoNhanThucEnum, name="muc_do_nhan_thuc_enum"),
        nullable=False,
    )

    TrangThaiDuyet: Mapped[TrangThaiDuyetEnum] = mapped_column(
        SAEnum(TrangThaiDuyetEnum, name="trang_thai_duyet_enum"),
        nullable=False,
        default=TrangThaiDuyetEnum.NHAP,
    )

    MaNguoiTao: Mapped[int] = mapped_column(
        ForeignKey("NguoiDung.MaNguoiDung", ondelete="RESTRICT"),
        nullable=False,
    )

    SoLanSuDung: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    NgayTao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    NgayCapNhat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=_utcnow,
        nullable=True,
    )

    # Chủ đề chứa câu hỏi
    chu_de: Mapped[ChuDe] = relationship(
        "ChuDe",
        back_populates="cau_hoi",
    )

    # Người tạo câu hỏi
    nguoi_tao: Mapped[NguoiDung] = relationship(
        "NguoiDung",
        back_populates="cau_hoi",
    )

    # Các lựa chọn trả lời
    lua_chon: Mapped[list[LuaChonCauHoi]] = relationship(
        "LuaChonCauHoi",
        back_populates="cau_hoi",
        cascade="all, delete-orphan",
        order_by="LuaChonCauHoi.ThuTuHienThi",
    )

    # Từ khóa gắn với câu hỏi
    tu_khoa_lien_ket: Mapped[list[CauHoiNH_TuKhoa]] = relationship(
        "CauHoiNH_TuKhoa",
        back_populates="cau_hoi",
        cascade="all, delete-orphan",
    )

    # Tệp đính kèm
    tep_dinh_kem: Mapped[list[TepDinhKemCauHoi]] = relationship(
        "TepDinhKemCauHoi",
        back_populates="cau_hoi",
        cascade="all, delete-orphan",
    )

    # Lịch sử chỉnh sửa
    lich_su_chinh_sua: Mapped[list[LichSuChinhSuaCauHoi]] = relationship(
        "LichSuChinhSuaCauHoi",
        back_populates="cau_hoi",
        cascade="all, delete-orphan",
    )

    # Quan hệ với bảng trung gian câu hỏi - đề thi
    de_thi_lien_ket: Mapped[list[DeThi_CauHoi]] = relationship(
        "DeThi_CauHoi",
        back_populates="cau_hoi",
    )
\
class LuaChonCauHoi(Base):
    __tablename__ = "LuaChonCauHoi"

    MaLuaChon: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    MaCauHoiNH: Mapped[int] = mapped_column(
        ForeignKey("CauHoiNganHang.MaCauHoiNH", ondelete="CASCADE"),
        nullable=False,
    )

    NoiDungLuaChon: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    LaDapAnDung: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    ThuTuHienThi: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    cau_hoi: Mapped[CauHoiNganHang] = relationship(
        "CauHoiNganHang",
        back_populates="lua_chon",
    )


class TuKhoa(Base):
    __tablename__ = "TuKhoa"

    MaTuKhoa: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    TenTuKhoa: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    cau_hoi_lien_ket: Mapped[list[CauHoiNH_TuKhoa]] = relationship(
        "CauHoiNH_TuKhoa",
        back_populates="tu_khoa",
        cascade="all, delete-orphan",
    )




class CauHoiNH_TuKhoa(Base):
    __tablename__ = "CauHoiNH_TuKhoa"

    MaCauHoiNH: Mapped[int] = mapped_column(
        ForeignKey("CauHoiNganHang.MaCauHoiNH", ondelete="CASCADE"),
        primary_key=True,
    )

    MaTuKhoa: Mapped[int] = mapped_column(
        ForeignKey("TuKhoa.MaTuKhoa", ondelete="CASCADE"),
        primary_key=True,
    )

    cau_hoi: Mapped[CauHoiNganHang] = relationship(
        "CauHoiNganHang",
        back_populates="tu_khoa_lien_ket",
    )

    tu_khoa: Mapped[TuKhoa] = relationship(
        "TuKhoa",
        back_populates="cau_hoi_lien_ket",
    )


# ============================================================
# 6. TEP DINH KEM CAU HOI
# ============================================================

class TepDinhKemCauHoi(Base):
    __tablename__ = "TepDinhKemCauHoi"

    MaTep: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    MaCauHoiNH: Mapped[int] = mapped_column(
        ForeignKey("CauHoiNganHang.MaCauHoiNH", ondelete="CASCADE"),
        nullable=False,
    )

    DuongDanTep: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    LoaiTep: Mapped[LoaiTepEnum] = mapped_column(
        SAEnum(LoaiTepEnum, name="loai_tep_enum"),
        nullable=False,
    )

    cau_hoi: Mapped[CauHoiNganHang] = relationship(
        "CauHoiNganHang",
        back_populates="tep_dinh_kem",
    )


# ============================================================
# 7. LICH SU CHINH SUA CAU HOI
# ============================================================

class LichSuChinhSuaCauHoi(Base):
    __tablename__ = "LichSuChinhSuaCauHoi"

    MaLichSu: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    MaCauHoiNH: Mapped[int] = mapped_column(
        ForeignKey("CauHoiNganHang.MaCauHoiNH", ondelete="CASCADE"),
        nullable=False,
    )

    MaNguoiChinhSua: Mapped[int | None] = mapped_column(
        ForeignKey("NguoiDung.MaNguoiDung", ondelete="SET NULL"),
        nullable=True,
    )

    NoiDungTruoc: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    NgayChinhSua: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    cau_hoi: Mapped[CauHoiNganHang] = relationship(
        "CauHoiNganHang",
        back_populates="lich_su_chinh_sua",
    )

    nguoi_chinh_sua: Mapped[NguoiDung | None] = relationship(
        "NguoiDung",
        back_populates="lich_su_sua",
    )
