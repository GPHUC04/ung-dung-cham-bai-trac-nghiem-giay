"""
services/export.py — Export Bảng điểm & Thống kê ra Excel (.xlsx) & CSV (GV-08)
Tương thích với các phần mềm quản lý trường học (VNEdu, SMAS...).
"""
import io
import csv
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.models.chambai import PhieuTraLoi, KetQua, TrangThaiPhieuEnum
from app.models.dethi import DeThi
from app.models.lophoc import Lop, HocSinh


def export_bang_diem_excel(
    db: Session,
    ma_de_thi: int,
    ma_lop: Optional[int] = None
) -> Tuple[io.BytesIO, str]:
    """
    Xuất bảng điểm toàn bộ học sinh theo Lớp / Đề thi thành tệp Excel (.xlsx)
    được định dạng đẹp mắt (tiêu đề, màu sắc, phông chữ Inter/Calibri).
    """
    de_thi = db.query(DeThi).filter(DeThi.MaDeThi == ma_de_thi).first()
    ten_de = de_thi.TenDeThi if de_thi else "Đề thi"

    query = (
        db.query(PhieuTraLoi)
        .options(
            joinedload(PhieuTraLoi.hoc_sinh),
            joinedload(PhieuTraLoi.lop),
            joinedload(PhieuTraLoi.ma_de),
            joinedload(PhieuTraLoi.ket_qua),
        )
        .filter(PhieuTraLoi.MaDeThi == ma_de_thi)
        .filter(PhieuTraLoi.TrangThai.in_([TrangThaiPhieuEnum.DA_CHAM_XONG, TrangThaiPhieuEnum.DA_CHINH_SUA, TrangThaiPhieuEnum.DA_LUU]))
    )
    if ma_lop:
        query = query.filter(PhieuTraLoi.MaLop == ma_lop)

    phieus = query.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Bảng Điểm"

    # Header title
    ws.merge_cells("A1:G1")
    ws["A1"] = f"BẢNG ĐIỂM CHI TIẾT - {ten_de.upper()}"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="1F2937")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    # Table columns
    headers = ["STT", "SBD", "Họ và Tên", "Lớp", "Mã Đề", "Số Câu Đúng", "Điểm Số"]
    ws.append([])  # Row 2 empty
    ws.append(headers)  # Row 3 headers

    # Header style
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for col_idx in range(1, 8):
        cell = ws.cell(row=3, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB")
    )

    for idx, p in enumerate(phieus, start=1):
        hs_name = p.hoc_sinh.HoTen if p.hoc_sinh else "Chưa gán"
        sbd = p.hoc_sinh.SoBaoDanh if p.hoc_sinh else "-"
        lop_name = p.lop.TenLop if p.lop else "-"
        ma_de = p.ma_de.SoHieuMaDe if p.ma_de else "-"
        so_dung = p.ket_qua.SoCauDung if p.ket_qua else 0
        diem = p.ket_qua.Diem if p.ket_qua else 0.0

        row_data = [idx, sbd, hs_name, lop_name, ma_de, so_dung, diem]
        ws.append(row_data)

        row_num = idx + 3
        for col_idx in range(1, 8):
            c = ws.cell(row=row_num, column=col_idx)
            c.border = thin_border
            if col_idx in [1, 2, 4, 5, 6]:
                c.alignment = Alignment(horizontal="center")
            elif col_idx == 7:
                c.alignment = Alignment(horizontal="right")
                c.font = Font(bold=True)

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"Bang_Diem_De_{ma_de_thi}.xlsx"
    return output, filename


def export_bang_diem_csv(
    db: Session,
    ma_de_thi: int,
    ma_lop: Optional[int] = None
) -> Tuple[str, str]:
    """Xuất bảng điểm dạng UTF-8 CSV."""
    query = (
        db.query(PhieuTraLoi)
        .options(
            joinedload(PhieuTraLoi.hoc_sinh),
            joinedload(PhieuTraLoi.lop),
            joinedload(PhieuTraLoi.ma_de),
            joinedload(PhieuTraLoi.ket_qua),
        )
        .filter(PhieuTraLoi.MaDeThi == ma_de_thi)
        .filter(PhieuTraLoi.TrangThai.in_([TrangThaiPhieuEnum.DA_CHAM_XONG, TrangThaiPhieuEnum.DA_CHINH_SUA, TrangThaiPhieuEnum.DA_LUU]))
    )
    if ma_lop:
        query = query.filter(PhieuTraLoi.MaLop == ma_lop)

    phieus = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["STT", "SoBaoDanh", "HoTen", "Lop", "MaDe", "SoCauDung", "Diem"])

    for idx, p in enumerate(phieus, start=1):
        hs_name = p.hoc_sinh.HoTen if p.hoc_sinh else "Chưa gán"
        sbd = p.hoc_sinh.SoBaoDanh if p.hoc_sinh else "-"
        lop_name = p.lop.TenLop if p.lop else "-"
        ma_de = p.ma_de.SoHieuMaDe if p.ma_de else "-"
        so_dung = p.ket_qua.SoCauDung if p.ket_qua else 0
        diem = p.ket_qua.Diem if p.ket_qua else 0.0

        writer.writerow([idx, sbd, hs_name, lop_name, ma_de, so_dung, diem])

    filename = f"Bang_Diem_De_{ma_de_thi}.csv"
    return output.getvalue(), filename
