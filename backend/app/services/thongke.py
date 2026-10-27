"""
services/thongke.py — Engine Thống kê Phân tích Kết quả Thi & Độ khó Câu hỏi (GV-09, AD-07)
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.chambai import PhieuTraLoi, ChiTietBaiLam, KetQua, TrangThaiPhieuEnum
from app.models.dethi import DeThi, DeThi_CauHoi
from app.models.lophoc import Lop
from app.models.nganhang import CauHoiNganHang
from app.schemas.thongke import ThongKeLopResponse, PhoDiemItem, ThongKeCauHoiItem


def tinh_thong_ke_lop(
    db: Session,
    ma_de_thi: int,
    ma_lop: Optional[int] = None
) -> ThongKeLopResponse:
    """Tính toán thống kê điểm số (Phổ điểm, Điểm TB, Tỉ lệ Xếp loại) theo Đề thi và Lớp học."""
    de_thi = db.query(DeThi).filter(DeThi.MaDeThi == ma_de_thi).first()
    if not de_thi:
        raise ValueError("Đề thi không tồn tại.")

    ten_lop = "Tất cả các lớp"
    if ma_lop:
        lop = db.query(Lop).filter(Lop.MaLop == ma_lop).first()
        if lop:
            ten_lop = lop.TenLop

    # Lấy danh sách kết quả của các phiếu DA_LUU (hoặc DA_CHAM_XONG)
    query = (
        db.query(KetQua)
        .join(PhieuTraLoi, KetQua.MaPhieu == PhieuTraLoi.MaPhieu)
        .filter(PhieuTraLoi.MaDeThi == ma_de_thi)
        .filter(PhieuTraLoi.TrangThai.in_([TrangThaiPhieuEnum.DA_CHAM_XONG, TrangThaiPhieuEnum.DA_LUU]))
    )
    if ma_lop:
        query = query.filter(PhieuTraLoi.MaLop == ma_lop)

    ket_quas = query.all()

    if not ket_quas:
        return ThongKeLopResponse(
            MaLop=ma_lop,
            TenLop=ten_lop,
            MaDeThi=ma_de_thi,
            TenDeThi=de_thi.TenDeThi,
            TongSoPhieu=0,
            DiemTrungBinh=0.0,
            DiemCaoNhat=0.0,
            DiemThapNhat=0.0,
            TiLeGioi=0.0,
            TiLeKha=0.0,
            TiLeTrungBinh=0.0,
            TiLeYeu=0.0,
            PhoDiem=[]
        )

    diems = [kq.Diem for kq in ket_quas]
    n = len(diems)

    dtb = round(sum(diems) / n, 2)
    max_d = max(diems)
    min_d = min(diems)

    gioi = sum(1 for d in diems if d >= 8.0)
    kha = sum(1 for d in diems if 6.5 <= d < 8.0)
    tb = sum(1 for d in diems if 5.0 <= d < 6.5)
    yeu = sum(1 for d in diems if d < 5.0)

    # Phổ điểm 10 khoảng (0-1, 1-2 ... 9-10)
    buckets = [0] * 10
    for d in diems:
        idx = min(9, int(d))
        buckets[idx] += 1

    pho_diem = [
        PhoDiemItem(KhoangDiem=f"{i}.0 - {i+1}.0", SoLuong=buckets[i])
        for i in range(10)
    ]

    return ThongKeLopResponse(
        MaLop=ma_lop,
        TenLop=ten_lop,
        MaDeThi=ma_de_thi,
        TenDeThi=de_thi.TenDeThi,
        TongSoPhieu=n,
        DiemTrungBinh=dtb,
        DiemCaoNhat=max_d,
        DiemThapNhat=min_d,
        TiLeGioi=round((gioi / n) * 100, 1),
        TiLeKha=round((kha / n) * 100, 1),
        TiLeTrungBinh=round((tb / n) * 100, 1),
        TiLeYeu=round((yeu / n) * 100, 1),
        PhoDiem=pho_diem
    )


def tinh_thong_ke_cau_hoi(
    db: Session,
    ma_de_thi: int
) -> List[ThongKeCauHoiItem]:
    """Phân tích tỉ lệ đúng/sai và độ khó thực tế từng câu hỏi trong đề thi."""
    cau_hois = (
        db.query(DeThi_CauHoi)
        .filter(DeThi_CauHoi.MaDeThi == ma_de_thi)
        .order_by(DeThi_CauHoi.SoThuTuGoc)
        .all()
    )

    res = []
    for dt_ch in cau_hois:
        ch_nh = db.query(CauHoiNganHang).filter(CauHoiNganHang.MaCauHoiNH == dt_ch.MaCauHoiNH).first()
        noi_dung = ch_nh.NoiDung if ch_nh else f"Câu hỏi #{dt_ch.MaCauHoiNH}"

        # Tìm các ChiTietBaiLam của câu hỏi này trong các phiếu đã làm
        details = (
            db.query(ChiTietBaiLam)
            .join(PhieuTraLoi, ChiTietBaiLam.MaPhieu == PhieuTraLoi.MaPhieu)
            .filter(PhieuTraLoi.MaDeThi == ma_de_thi)
            .filter(ChiTietBaiLam.MaDeThiCauHoi == dt_ch.MaDeThiCauHoi)
            .all()
        )

        total_lam = len(details)
        if total_lam == 0:
            res.append(ThongKeCauHoiItem(
                MaDeThiCauHoi=dt_ch.MaDeThiCauHoi,
                SoThuTuGoc=dt_ch.SoThuTuGoc,
                NoiDungCauHoi=noi_dung,
                SoLuotLam=0,
                SoLuotDung=0,
                TiLeDung=0.0,
                PhanBoiDapAn={"A": 0, "B": 0, "C": 0, "D": 0}
            ))
            continue

        so_dung = 0
        dist = {"A": 0, "B": 0, "C": 0, "D": 0, "BO_TRONG": 0}

        for d in details:
            ans = d.DapAnDaChon
            if not ans:
                dist["BO_TRONG"] += 1
            else:
                dist[ans] = dist.get(ans, 0) + 1

            # Check matching correctness if DapAnDung exists for its MaMaDe
            if d.phieu and d.phieu.ma_de:
                da_correct = next((da.DapAnDung for da in d.phieu.ma_de.dap_an_dung if da.MaDeThiCauHoi == dt_ch.MaDeThiCauHoi), None)
                if ans == da_correct:
                    so_dung += 1

        ti_le_dung = round((so_dung / total_lam) * 100, 1)

        res.append(ThongKeCauHoiItem(
            MaDeThiCauHoi=dt_ch.MaDeThiCauHoi,
            SoThuTuGoc=dt_ch.SoThuTuGoc,
            NoiDungCauHoi=noi_dung,
            SoLuotLam=total_lam,
            SoLuotDung=so_dung,
            TiLeDung=ti_le_dung,
            PhanBoiDapAn=dist
        ))

    return res
