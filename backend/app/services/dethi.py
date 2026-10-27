"""
services/dethi.py — Service xử lý tráo đề thi & Sinh mã đề hoán vị (GV-11)
Đảm bảo:
- Hoán vị ngẫu nhiên thứ tự câu hỏi
- Hoán vị ngẫu nhiên phương án A/B/C/D
- Xác định và lưu vết chính xác ký tự đáp án đúng (A/B/C/D) cho từng mã đề vào bảng DapAnDung
- Tăng SoLanSuDung cho các câu hỏi ngân hàng được sử dụng
"""
import random
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.dethi import DeThi, DeThi_CauHoi, MaDe, DapAnDung
from app.models.nganhang import CauHoiNganHang, LuaChonCauHoi
from app.schemas.dethi import SinhMaDeRequest

OPTION_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"]


def tao_danh_sach_ma_de(
    db: Session,
    de_thi: DeThi,
    payload: SinhMaDeRequest
) -> List[MaDe]:
    """
    Hàm core tráo đề:
    Sinh out `so_luong_ma_de` mã đề với thứ tự câu hỏi và phương án đáp án được xáo trộn.
    """
    cau_hoi_list: List[DeThi_CauHoi] = (
        db.query(DeThi_CauHoi)
        .filter(DeThi_CauHoi.MaDeThi == de_thi.MaDeThi)
        .order_by(DeThi_CauHoi.SoThuTuGoc)
        .all()
    )

    if not cau_hoi_list:
        raise HTTPException(status_code=400, detail="Đề thi chưa có câu hỏi nào để tráo.")

    generated_ma_de_list = []

    for i in range(payload.so_luong_ma_de):
        # Số hiệu mã đề: VD '101', '102', '103'
        so_hieu = f"{payload.tien_to_ma_de}{i + 1:01d}" if payload.tien_to_ma_de else f"{101 + i}"

        # Copy danh sách câu hỏi để xáo
        shuffled_questions = list(cau_hoi_list)
        if payload.xao_cau_hoi:
            random.shuffle(shuffled_questions)

        thu_tu_json = {}
        ma_de_record = MaDe(
            MaDeThi=de_thi.MaDeThi,
            SoHieuMaDe=so_hieu,
            ThuTuCauHoi_JSON={}
        )
        db.add(ma_de_record)
        db.flush()  # Sinh MaMaDe

        for pos_idx, dt_ch in enumerate(shuffled_questions, start=1):
            thu_tu_json[str(pos_idx)] = dt_ch.MaDeThiCauHoi

            # Lấy danh sách đáp án của câu hỏi từ Ngân hàng
            options: List[LuaChonCauHoi] = (
                db.query(LuaChonCauHoi)
                .filter(LuaChonCauHoi.MaCauHoiNH == dt_ch.MaCauHoiNH)
                .order_by(LuaChonCauHoi.ThuTuHienThi)
                .all()
            )

            shuffled_options = list(options)
            if payload.xao_dap_an:
                random.shuffle(shuffled_options)

            # Tìm xem đáp án đúng rơi vào chữ cái nào (A, B, C, D)
            dap_an_dung_letter = "A"
            for opt_idx, opt in enumerate(shuffled_options):
                if opt.LaDapAnDung:
                    dap_an_dung_letter = OPTION_LETTERS[opt_idx] if opt_idx < len(OPTION_LETTERS) else "A"
                    break

            # Tạo bản ghi DapAnDung
            dap_an_record = DapAnDung(
                MaDeThiCauHoi=dt_ch.MaDeThiCauHoi,
                MaMaDe=ma_de_record.MaMaDe,
                DapAnDung=dap_an_dung_letter
            )
            db.add(dap_an_record)

        ma_de_record.ThuTuCauHoi_JSON = thu_tu_json
        generated_ma_de_list.append(ma_de_record)

    # Tăng SoLanSuDung trong Ngân Hàng Câu Hỏi
    for dt_ch in cau_hoi_list:
        db.query(CauHoiNganHang).filter(
            CauHoiNganHang.MaCauHoiNH == dt_ch.MaCauHoiNH
        ).update(
            {CauHoiNganHang.SoLanSuDung: CauHoiNganHang.SoLanSuDung + 1},
            synchronize_session=False
        )

    db.commit()
    return generated_ma_de_list
