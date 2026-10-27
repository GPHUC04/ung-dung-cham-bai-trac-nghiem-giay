
"""
models/chambai.py — Nhóm 6: Chấm bài & Kết quả (4 bảng)

- PhieuTraLoi: Một lần chụp/quét phiếu trả lời (GV-03/GV-04)
- ChiTietBaiLam: Đáp án học sinh từng câu, kết quả từ OpenCV (GV-05)
- KetQua: Điểm tổng hợp 1-1 với PhieuTraLoi (GV-06/07/08)
- ThongKeCauHoi: Phân tích thống kê câu hỏi (GV thống kê / AD-07)
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.dethi import DeThi, DeThi_CauHoi, MaDe
    from app.models.lophoc import HocSinh, Lop
    from app.models.nguoidung import NguoiDung


def _utcnow() -> datetime:
    """Lấy thời điểm hiện tại theo UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


# ============================================================
# 1. ENUM TRẠNG THÁI PHIẾU
# ============================================================

class TrangThaiPhieuEnum(str, enum.Enum):
    """Trạng thái vòng đời phiếu trả lời."""

    MOI_CHUP = "MOI_CHUP"
    DANG_XU_LY = "DANG_XU_LY"
    XU_LY_LOI = "XU_LY_LOI"
    CAN_XEM_LAI = "CAN_XEM_LAI"
    DA_CHAM_XONG = "DA_CHAM_XONG"
    DA_CHINH_SUA = "DA_CHINH_SUA"
    DA_LUU = "DA_LUU"


# ============================================================
# 2. PHIẾU TRẢ LỜI
# ============================================================

class PhieuTraLoi(Base):
    """
    Một lần chụp/quét phiếu trả lời của học sinh.

    MaHocSinh và MaMaDe có thể NULL khi chưa xác định.
    MaLop được lưu để hỗ trợ thống kê theo lớp.
    """

    __tablename__ = "PhieuTraLoi"

    MaPhieu: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    MaDeThi: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("DeThi.MaDeThi", ondelete="RESTRICT"),
        nullable=False,
        comment="Đề thi của phiếu",
    )

    MaHocSinh: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("HocSinh.MaHocSinh", ondelete="SET NULL"),
        nullable=True,
        comment="Học sinh sở hữu phiếu",
    )

    MaMaDe: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("MaDe.MaMaDe", ondelete="RESTRICT"),
        nullable=True,
        comment="Mã đề học sinh làm",
    )

    MaLop: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("Lop.MaLop", ondelete="SET NULL"),
        nullable=True,
        comment="Lớp học phục vụ thống kê",
    )

    MaNguoiDung: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("NguoiDung.MaNguoiDung", ondelete="RESTRICT"),
        nullable=False,
        comment="Giáo viên thực hiện chấm",
    )

    DuongDanAnhGoc: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="URL ảnh gốc trên Supabase Storage",
    )

    ThoiGianQuet: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    TrangThai: Mapped[TrangThaiPhieuEnum] = mapped_column(
        Enum(TrangThaiPhieuEnum, name="trangthai_phieu_enum"),
        default=TrangThaiPhieuEnum.MOI_CHUP,
        nullable=False,
    )

    # Relationships

    de_thi: Mapped[DeThi] = relationship(
        "DeThi",
        back_populates="phieu_tra_loi",
    )

    hoc_sinh: Mapped[HocSinh | None] = relationship(
        "HocSinh",
        back_populates="phieu_tra_loi",
    )

    ma_de: Mapped[MaDe | None] = relationship(
        "MaDe",
        back_populates="phieu_tra_loi",
    )

    lop: Mapped[Lop | None] = relationship(
        "Lop",
        back_populates="phieu_tra_loi",
        foreign_keys=[MaLop],
    )

    giao_vien_cham: Mapped[NguoiDung] = relationship(
        "NguoiDung",
        back_populates="phieu_tra_loi",
    )

    chi_tiet_bai_lam: Mapped[list[ChiTietBaiLam]] = relationship(
        "ChiTietBaiLam",
        back_populates="phieu",
        cascade="all, delete-orphan",
    )

    ket_qua: Mapped[KetQua | None] = relationship(
        "KetQua",
        back_populates="phieu",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Properties

    @property
    def TenHocSinh(self) -> str | None:
        return self.hoc_sinh.HoTen if self.hoc_sinh else None

    @property
    def SoBaoDanh(self) -> str | None:
        return self.hoc_sinh.SoBaoDanh if self.hoc_sinh else None

    @property
    def SoHieuMaDe(self) -> str | None:
        return self.ma_de.SoHieuMaDe if self.ma_de else None

    def __repr__(self) -> str:
        return f"<PhieuTraLoi #{self.MaPhieu} [{self.TrangThai}]>"


# ============================================================
# 3. CHI TIẾT BÀI LÀM
# ============================================================

class ChiTietBaiLam(Base):
    """
    Đáp án học sinh đã chọn cho từng câu, nhận diện từ OpenCV.

    DapAnDaChon = NULL nếu học sinh bỏ trống.
    DoTinCay: confidence score trong khoảng 0.0–1.0.
    CoBatThuong = True nếu ô tô không rõ hoặc tô nhiều ô.
    """

    __tablename__ = "ChiTietBaiLam"

    MaChiTiet: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    MaPhieu: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("PhieuTraLoi.MaPhieu", ondelete="CASCADE"),
        nullable=False,
    )

    MaDeThiCauHoi: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "DeThi_CauHoi.MaDeThiCauHoi",
            ondelete="RESTRICT",
        ),
        nullable=False,
        comment="Câu hỏi tương ứng trong đề thi",
    )

    DapAnDaChon: Mapped[str | None] = mapped_column(
        String(1),
        nullable=True,
        comment="Đáp án đã tô A/B/C/D; NULL nếu bỏ trống",
    )

    DoTinCay: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Confidence score từ OpenCV",
    )

    CoBatThuong: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Ô tô bất thường, cần giáo viên xem lại",
    )

    # Relationships

    phieu: Mapped[PhieuTraLoi] = relationship(
        "PhieuTraLoi",
        back_populates="chi_tiet_bai_lam",
    )

    de_thi_cau_hoi: Mapped[DeThi_CauHoi] = relationship(
        "DeThi_CauHoi",
        back_populates="chi_tiet_bai_lam",
    )

    # Properties

    @property
    def DapAnDung(self) -> str | None:
        """Lấy đáp án đúng từ mã đề của phiếu."""
        if self.phieu and self.phieu.ma_de:
            for dap_an in self.phieu.ma_de.dap_an_dung:
                if dap_an.MaDeThiCauHoi == self.MaDeThiCauHoi:
                    return dap_an.DapAnDung

        return None

    @property
    def LaDung(self) -> bool:
        """Kiểm tra đáp án học sinh có đúng hay không."""
        dap_an_dung = self.DapAnDung

        if not self.DapAnDaChon or not dap_an_dung:
            return False

        return self.DapAnDaChon == dap_an_dung

    @property
    def SoThuTuMoi(self) -> int | None:
        """Xác định số thứ tự câu hỏi sau khi hoán vị mã đề."""
        if (
            self.phieu
            and self.phieu.ma_de
            and self.phieu.ma_de.ThuTuCauHoi_JSON
        ):
            for thu_tu, ma_cau_hoi in (
                self.phieu.ma_de.ThuTuCauHoi_JSON.items()
            ):
                if ma_cau_hoi == self.MaDeThiCauHoi:
                    try:
                        return int(thu_tu)
                    except (ValueError, TypeError):
                        return None

        if self.de_thi_cau_hoi:
            return self.de_thi_cau_hoi.SoThuTuGoc

        return None

    def __repr__(self) -> str:
        return (
            f"<ChiTietBaiLam Phiếu#{self.MaPhieu} "
            f"Câu#{self.MaDeThiCauHoi} → {self.DapAnDaChon}>"
        )


# ============================================================
# 4. KẾT QUẢ
# ============================================================

class KetQua(Base):
    """
    Kết quả tổng hợp, quan hệ 1-1 với PhieuTraLoi.

    DaChinhSuaThuCong = True nếu giáo viên đã sửa đáp án thủ công.
    Công thức tính điểm được xử lý tại tầng service.
    """

    __tablename__ = "KetQua"

    MaKetQua: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    MaPhieu: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("PhieuTraLoi.MaPhieu", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    SoCauDung: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Tổng số câu đúng",
    )

    SoCauSai: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Tổng số câu sai",
    )

    SoCauBoTrong: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Tổng số câu bỏ trống",
    )

    Diem: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Điểm quy đổi, thường theo thang 10",
    )

    DaChinhSuaThuCong: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Đã qua bước sửa tay GV-07",
    )

    # Relationships

    phieu: Mapped[PhieuTraLoi] = relationship(
        "PhieuTraLoi",
        back_populates="ket_qua",
    )

    def __repr__(self) -> str:
        return (
            f"<KetQua Phiếu#{self.MaPhieu} "
            f"Điểm={self.Diem} ({self.SoCauDung} đúng)>"
        )


# ============================================================
# 5. THỐNG KÊ CÂU HỎI
# ============================================================

class ThongKeCauHoi(Base):
    """
    Thống kê từng câu hỏi trong đề thi.

    DoKho_ThucTe: Tỉ lệ học sinh trả lời đúng, khoảng 0.0–1.0.
    DoPhanBiet: Chỉ số phân biệt giữa học sinh giỏi và yếu.
    """

    __tablename__ = "ThongKeCauHoi"

    __table_args__ = (
        UniqueConstraint(
            "MaDeThiCauHoi",
            name="uq_thongke_dethicauhoi",
        ),
    )

    MaThongKe: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    MaDeThiCauHoi: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "DeThi_CauHoi.MaDeThiCauHoi",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    DoKho_ThucTe: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Tỉ lệ học sinh trả lời đúng, khoảng 0.0–1.0",
    )

    DoPhanBiet: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Chỉ số phân biệt giữa học sinh giỏi và yếu",
    )

    # Relationships

    de_thi_cau_hoi: Mapped[DeThi_CauHoi] = relationship(
        "DeThi_CauHoi",
        back_populates="thong_ke",
    )
