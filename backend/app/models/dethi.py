
"""
models/dethi.py — Nhóm 5: Đề thi & Mã đề (4 bảng)

Các model:
1. DeThi: Đề thi gốc (GV-10)
2. DeThi_CauHoi: Câu hỏi trong đề, vị trí gốc
3. MaDe: Mã đề hoán vị (GV-11)
4. DapAnDung: Đáp án đúng theo từng mã đề

Thiết kế then chốt:
- MaDe.ThuTuCauHoi_JSON:
  Ánh xạ {vị_trí_mới: MaDeThiCauHoi}.
- DapAnDung.DapAnDung:
  Lưu ký tự A/B/C/D đúng sau khi hoán vị lựa chọn.
  Đây là nguồn đáp án chuẩn để chấm bài.

SQLAlchemy 2.0:
- Mapped
- mapped_column
- Declarative Base dùng chung
- Relationship có kiểu dữ liệu
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


if TYPE_CHECKING:
    from app.models.danhmuc import DanhMucChung
    from app.models.nguoidung import NguoiDung
    from app.models.nganhang import CauHoiNganHang
    from app.models.chambai import PhieuTraLoi, ChiTietBaiLam, ThongKeCauHoi


def _utcnow() -> datetime:
    """Lấy thời điểm hiện tại theo UTC."""
    return datetime.now(timezone.utc)


class DeThi(Base):
    """
    Đề thi trắc nghiệm gốc do giáo viên tạo (GV-10).

    Một đề thi có nhiều câu hỏi và có thể sinh nhiều mã đề.
    """

    __tablename__ = "DeThi"

    MaDeThi: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    TenDeThi: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Tên đề thi",
    )

    MaDanhMuc: Mapped[int] = mapped_column(
        ForeignKey(
            "DanhMucChung.MaDanhMuc",
            ondelete="RESTRICT",
        ),
        nullable=False,
        comment="Môn học thuộc danh mục MON_HOC",
    )

    SoCau: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Tổng số câu hỏi trong đề",
    )

    SoLuaChon: Mapped[int] = mapped_column(
        SmallInteger,
        default=4,
        nullable=False,
        comment="Số lựa chọn mỗi câu, thường là 4",
    )

    MaNguoiDung: Mapped[int] = mapped_column(
        ForeignKey(
            "NguoiDung.MaNguoiDung",
            ondelete="RESTRICT",
        ),
        nullable=False,
        comment="Giáo viên tạo đề",
    )

    NgayTao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    # Quan hệ với danh mục môn học
    mon_hoc: Mapped[DanhMucChung] = relationship(
        "DanhMucChung",
        back_populates="de_thi",
    )

    # Giáo viên tạo đề
    giao_vien: Mapped[NguoiDung] = relationship(
        "NguoiDung",
        back_populates="de_thi",
    )

    # Các câu hỏi trong đề, theo thứ tự gốc
    cau_hoi_list: Mapped[list[DeThi_CauHoi]] = relationship(
        "DeThi_CauHoi",
        back_populates="de_thi",
        cascade="all, delete-orphan",
        order_by="DeThi_CauHoi.SoThuTuGoc",
    )

    # Các mã đề được sinh từ đề gốc
    ma_de_list: Mapped[list[MaDe]] = relationship(
        "MaDe",
        back_populates="de_thi",
        cascade="all, delete-orphan",
    )

    # Các phiếu trả lời thuộc đề thi
    phieu_tra_loi: Mapped[list[PhieuTraLoi]] = relationship(
        "PhieuTraLoi",
        back_populates="de_thi",
    )

    def __repr__(self) -> str:
        return (
            f"<DeThi #{self.MaDeThi} "
            f"'{self.TenDeThi}' ({self.SoCau} câu)>"
        )


class DeThi_CauHoi(Base):
    """
    Bảng liên kết đề thi với câu hỏi ngân hàng.

    MaDeThiCauHoi là định danh của một câu hỏi trong một đề cụ thể.
    SoThuTuGoc lưu vị trí của câu hỏi trước khi hoán vị.

    Việc tăng CauHoiNganHang.SoLanSuDung được xử lý ở tầng service.
    """

    __tablename__ = "DeThi_CauHoi"

    __table_args__ = (
        UniqueConstraint(
            "MaDeThi",
            "SoThuTuGoc",
            name="uq_dethi_cauhoi_thutu_goc",
        ),
        UniqueConstraint(
            "MaDeThi",
            "MaCauHoiNH",
            name="uq_dethi_cauhoi_cau_hoi",
        ),
    )

    MaDeThiCauHoi: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    MaDeThi: Mapped[int] = mapped_column(
        ForeignKey(
            "DeThi.MaDeThi",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    MaCauHoiNH: Mapped[int] = mapped_column(
        ForeignKey(
            "CauHoiNganHang.MaCauHoiNH",
            ondelete="RESTRICT",
        ),
        nullable=False,
        comment="Câu hỏi nguồn trong ngân hàng",
    )

    SoThuTuGoc: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Vị trí câu hỏi trong đề gốc",
    )

    # Đề thi gốc
    de_thi: Mapped[DeThi] = relationship(
        "DeThi",
        back_populates="cau_hoi_list",
    )

    # Câu hỏi ngân hàng
    # Tên back_populates khớp với models/nganhang.py đã cung cấp.
    cau_hoi: Mapped[CauHoiNganHang] = relationship(
        "CauHoiNganHang",
        back_populates="de_thi_lien_ket",
    )

    # Đáp án theo từng mã đề
    dap_an_dung: Mapped[list[DapAnDung]] = relationship(
        "DapAnDung",
        back_populates="de_thi_cau_hoi",
        cascade="all, delete-orphan",
    )

    # Các chi tiết bài làm tham chiếu câu hỏi này
    chi_tiet_bai_lam: Mapped[list[ChiTietBaiLam]] = relationship(
        "ChiTietBaiLam",
        back_populates="de_thi_cau_hoi",
    )

    # Thống kê câu hỏi nếu có bản ghi thống kê
    thong_ke: Mapped[ThongKeCauHoi | None] = relationship(
        "ThongKeCauHoi",
        back_populates="de_thi_cau_hoi",
        uselist=False,
    )

    def __repr__(self) -> str:
        return (
            f"<DeThi_CauHoi DeThi#{self.MaDeThi} "
            f"CauHoi#{self.MaCauHoiNH} "
            f"vi_tri={self.SoThuTuGoc}>"
        )


class MaDe(Base):
    """
    Mã đề hoán vị được sinh từ đề thi gốc.

    ThuTuCauHoi_JSON ánh xạ:
        vị trí mới -> MaDeThiCauHoi

    Ví dụ:
        {
            "1": 15,
            "2": 8,
            "3": 22
        }

    Nghĩa là câu số 1 trong mã đề tham chiếu bản ghi
    DeThi_CauHoi có MaDeThiCauHoi = 15.
    """

    __tablename__ = "MaDe"

    __table_args__ = (
        UniqueConstraint(
            "MaDeThi",
            "SoHieuMaDe",
            name="uq_made_so_hieu",
        ),
    )

    MaMaDe: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    MaDeThi: Mapped[int] = mapped_column(
        ForeignKey(
            "DeThi.MaDeThi",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    SoHieuMaDe: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Số hiệu mã đề hiển thị trên phiếu",
    )

    ThuTuCauHoi_JSON: Mapped[dict[str, int]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        comment="Ánh xạ vị trí mới sang MaDeThiCauHoi",
    )

    # Đề thi gốc sinh ra mã đề
    de_thi: Mapped[DeThi] = relationship(
        "DeThi",
        back_populates="ma_de_list",
    )

    # Đáp án chuẩn theo mã đề
    dap_an_dung: Mapped[list[DapAnDung]] = relationship(
        "DapAnDung",
        back_populates="ma_de",
        cascade="all, delete-orphan",
    )

    # Các phiếu trả lời sử dụng mã đề này
    phieu_tra_loi: Mapped[list[PhieuTraLoi]] = relationship(
        "PhieuTraLoi",
        back_populates="ma_de",
    )

    def __repr__(self) -> str:
        return (
            f"<MaDe #{self.SoHieuMaDe} "
            f"(DeThi#{self.MaDeThi})>"
        )


class DapAnDung(Base):
    """
    Đáp án đúng của một câu hỏi trong một mã đề cụ thể.

    DapAnDung lưu ký tự A/B/C/D sau khi hoán vị lựa chọn.
    Khi chấm bài, đối chiếu đáp án học sinh với bản ghi
    thuộc đúng MaMaDe đang sử dụng.

    Không tính lại đáp án đúng trong quá trình chấm.
    """

    __tablename__ = "DapAnDung"

    __table_args__ = (
        UniqueConstraint(
            "MaMaDe",
            "MaDeThiCauHoi",
            name="uq_dapan_made_cauhoi",
        ),
    )

    MaDapAn: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    MaDeThiCauHoi: Mapped[int] = mapped_column(
        ForeignKey(
            "DeThi_CauHoi.MaDeThiCauHoi",
            ondelete="CASCADE",
        ),
        nullable=False,
        comment="Câu hỏi thuộc đề thi gốc",
    )

    MaMaDe: Mapped[int] = mapped_column(
        ForeignKey(
            "MaDe.MaMaDe",
            ondelete="CASCADE",
        ),
        nullable=False,
        comment="Mã đề áp dụng",
    )

    DapAnDung: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
        comment="Ký tự đáp án đúng sau hoán vị",
    )

    # Câu hỏi trong đề
    de_thi_cau_hoi: Mapped[DeThi_CauHoi] = relationship(
        "DeThi_CauHoi",
        back_populates="dap_an_dung",
    )

    # Mã đề áp dụng
    ma_de: Mapped[MaDe] = relationship(
        "MaDe",
        back_populates="dap_an_dung",
    )

    @property
    def SoThuTuMoi(self) -> int | None:
        """
        Trả về vị trí mới của câu hỏi trong mã đề.

        Tra cứu ThuTuCauHoi_JSON theo MaDeThiCauHoi.
        """

        if self.ma_de is None or not self.ma_de.ThuTuCauHoi_JSON:
            return None

        for vi_tri, ma_cau_hoi in self.ma_de.ThuTuCauHoi_JSON.items():
            if ma_cau_hoi == self.MaDeThiCauHoi:
                try:
                    return int(vi_tri)
                except (ValueError, TypeError):
                    return None

        return None

    def __repr__(self) -> str:
        return (
            f"<DapAnDung MaDe#{self.MaMaDe} "
            f"CauHoi#{self.MaDeThiCauHoi} "
            f"-> {self.DapAnDung}>"
        )
