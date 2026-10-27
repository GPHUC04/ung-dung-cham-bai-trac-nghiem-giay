
"""
models/lophoc.py — Nhóm 3: Lớp học & Học sinh (2 bảng)
- Lop: Lớp học của giáo viên (GV-12)
- HocSinh: Danh sách học sinh (GV-12)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.danhmuc import DanhMucChung
    from app.models.nguoidung import NguoiDung
    from app.models.chambai import PhieuTraLoi


class Lop(Base):
    """
    Lớp học do giáo viên quản lý (GV-12).
    Một giáo viên có thể quản lý nhiều lớp.
    Lớp gắn với khối lớp qua DanhMucChung
    (LoaiDanhMuc=KHOI_LOP).
    """
    __tablename__ = "Lop"

    MaLop: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    TenLop: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="VD: 10A1, 11B2",
    )

    MaDanhMuc: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "DanhMucChung.MaDanhMuc",
            ondelete="RESTRICT",
        ),
        nullable=False,
        comment="Khối lớp (DanhMucChung.LoaiDanhMuc = KHOI_LOP)",
    )

    MaNguoiDung: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "NguoiDung.MaNguoiDung",
            ondelete="RESTRICT",
        ),
        nullable=False,
        comment="Giáo viên chủ nhiệm/phụ trách",
    )

    # Relationships
    khoi_lop: Mapped[DanhMucChung] = relationship(
        back_populates="lop_hoc",
    )

    giao_vien: Mapped[NguoiDung] = relationship(
        back_populates="lop_hoc",
    )

    hoc_sinh: Mapped[list[HocSinh]] = relationship(
        back_populates="lop",
        cascade="all, delete-orphan",
    )

    phieu_tra_loi: Mapped[list[PhieuTraLoi]] = relationship(
        back_populates="lop",
        foreign_keys="PhieuTraLoi.MaLop",
    )

    def __repr__(self) -> str:
        return f"<Lop {self.TenLop}>"


class HocSinh(Base):
    """
    Học sinh thuộc một lớp học (GV-12).
    SoBaoDanh duy nhất trong phạm vi lớp.
    Một học sinh có thể có nhiều phiếu trả lời.
    """
    __tablename__ = "HocSinh"

    __table_args__ = (
        UniqueConstraint(
            "MaLop",
            "SoBaoDanh",
            name="uq_hocsinh_lop_sbd",
        ),
    )

    MaHocSinh: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    HoTen: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Họ tên học sinh",
    )

    SoBaoDanh: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Số báo danh (duy nhất trong lớp)",
    )

    MaLop: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "Lop.MaLop",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # Relationships
    lop: Mapped[Lop] = relationship(
        back_populates="hoc_sinh",
    )

    phieu_tra_loi: Mapped[list[PhieuTraLoi]] = relationship(
        back_populates="hoc_sinh",
    )

    def __repr__(self) -> str:
        return f"<HocSinh {self.SoBaoDanh} - {self.HoTen}>"
