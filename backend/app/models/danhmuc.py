"""
models/danhmuc.py — Nhóm 2: Danh mục dùng chung (1 bảng đa dụng)
- DanhMucChung: Môn học + Khối lớp + Năm học (AD-03)
"""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.dethi import DeThi
    from app.models.lophoc import Lop
    from app.models.nganhang import ChuDe


class LoaiDanhMucEnum(str, enum.Enum):
    MON_HOC = "MON_HOC"
    KHOI_LOP = "KHOI_LOP"
    NAM_HOC = "NAM_HOC"


class DanhMucChung(Base):
    """
    Danh mục dùng chung toàn hệ thống (AD-03).
    Một bảng đa dụng phân biệt bởi LoaiDanhMuc:
    - MON_HOC: Toán, Lý, Hóa, ...
    - KHOI_LOP: Khối 10, Khối 11, Khối 12
    - NAM_HOC: 2024-2025, 2025-2026, ...

    Lưu ý: Không được xóa danh mục đang được dùng bởi đề thi/lớp học (AD-03 ngoại lệ).
    DB chặn việc này bằng ondelete=RESTRICT ở các bảng Lop, DeThi, ChuDe.

    Giới hạn của thiết kế bảng đa dụng: DB không biết FK nào phải trỏ tới loại nào
    (VD: Lop.MaDanhMuc phải là KHOI_LOP). Việc kiểm tra loại phải làm ở tầng
    service/API khi tạo Lop, DeThi, ChuDe.
    """
    __tablename__ = "DanhMucChung"
    __table_args__ = (
        # Không cho trùng tên trong cùng một loại (VD: hai môn "Toán").
        UniqueConstraint("LoaiDanhMuc", "TenDanhMuc", name="uq_danhmuc_loai_ten"),
    )

    MaDanhMuc: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    LoaiDanhMuc: Mapped[LoaiDanhMucEnum] = mapped_column(
        Enum(LoaiDanhMucEnum, name="loai_danhmuc_enum"),
        comment="Phân loại: môn học, khối lớp, hoặc năm học",
    )
    TenDanhMuc: Mapped[str] = mapped_column(
        String(100), comment="VD: 'Toán', 'Khối 10', '2024-2025'"
    )

    # Relationships (mỗi quan hệ chỉ có nghĩa với một loại danh mục)
    lop_hoc: Mapped[list[Lop]] = relationship(back_populates="khoi_lop")    # KHOI_LOP
    de_thi: Mapped[list[DeThi]] = relationship(back_populates="mon_hoc")    # MON_HOC
    chu_de: Mapped[list[ChuDe]] = relationship(back_populates="mon_hoc")    # MON_HOC

    def __repr__(self) -> str:
        return f"<DanhMucChung [{self.LoaiDanhMuc}] {self.TenDanhMuc}>"