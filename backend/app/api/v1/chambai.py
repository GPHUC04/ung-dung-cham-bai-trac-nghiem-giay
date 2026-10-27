"""
api/v1/chambai.py — API Chấm bài, Xem lại kết quả & Sửa tay (GV-03 đến GV-08)
Endpoints:
- POST /chambai/tai-len              — Tải ảnh phiếu trả lời lên chấm (chạy OMR OpenCV Engine)
- GET  /chambai/phieu                — Danh sách phiếu đã chấm (lọc theo đề thi, lớp, trạng thái)
- GET  /chambai/phieu/{ma_phieu}      — Xem chi tiết kết quả chấm 1 phiếu
- PUT  /chambai/phieu/{ma_phieu}/sua-tay — Giáo viên sửa tay đáp án / gán SBD / gán Mã đề (GV-07)
- POST /chambai/phieu/{ma_phieu}/chot-luu — Chốt lưu kết quả chính thức (DA_LUU)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.api.v1.deps import require_giao_vien
from app.models.nguoidung import NguoiDung
from app.models.dethi import DeThi, DeThi_CauHoi, MaDe, DapAnDung
from app.models.lophoc import Lop, HocSinh
from app.models.chambai import PhieuTraLoi, ChiTietBaiLam, KetQua, TrangThaiPhieuEnum
from app.schemas.chambai import (
    PhieuTraLoiResponse, PhieuTraLoiDetailResponse,
    CapNhatBaiLamRequest, KetQuaResponse
)
from app.services.omr import omr_engine

router = APIRouter(prefix="/chambai", tags=["Chấm bài OMR & Kết quả"])


def _recalculate_score(db: Session, phieu: PhieuTraLoi) -> KetQua:
    """Hàm hỗ trợ tính lại điểm số dựa trên ChiTietBaiLam & DapAnDung."""
    if not phieu.MaMaDe:
        # Nếu chưa có mã đề thì chưa tính điểm chuẩn được
        so_dung = 0
        so_sai = 0
        so_trong = db.query(ChiTietBaiLam).filter(
            ChiTietBaiLam.MaPhieu == phieu.MaPhieu,
            ChiTietBaiLam.DapAnDaChon.is_(None)
        ).count()
        tong_cau = db.query(ChiTietBaiLam).filter(ChiTietBaiLam.MaPhieu == phieu.MaPhieu).count() or 1
    else:
        # Lấy bản đồ đáp án đúng của MaDe này
        dap_an_map = {
            da.MaDeThiCauHoi: da.DapAnDung
            for da in db.query(DapAnDung).filter(DapAnDung.MaMaDe == phieu.MaMaDe).all()
        }
        details = db.query(ChiTietBaiLam).filter(ChiTietBaiLam.MaPhieu == phieu.MaPhieu).all()

        so_dung = 0
        so_sai = 0
        so_trong = 0
        tong_cau = len(details) or 1

        for dt in details:
            correct_ans = dap_an_map.get(dt.MaDeThiCauHoi)
            if not dt.DapAnDaChon:
                so_trong += 1
            elif dt.DapAnDaChon == correct_ans:
                so_dung += 1
            else:
                so_sai += 1

    diem = round((so_dung / tong_cau) * 10.0, 2)

    ket_qua = db.query(KetQua).filter(KetQua.MaPhieu == phieu.MaPhieu).first()
    if not ket_qua:
        ket_qua = KetQua(
            MaPhieu=phieu.MaPhieu,
            SoCauDung=so_dung,
            SoCauSai=so_sai,
            SoCauBoTrong=so_trong,
            Diem=diem,
            DaChinhSuaThuCong=False
        )
        db.add(ket_qua)
    else:
        ket_qua.SoCauDung = so_dung
        ket_qua.SoCauSai = so_sai
        ket_qua.SoCauBoTrong = so_trong
        ket_qua.Diem = diem

    db.commit()
    db.refresh(ket_qua)
    return ket_qua


@router.post("/tai-len", response_model=PhieuTraLoiDetailResponse, status_code=status.HTTP_201_CREATED)
async def cham_phieu_anh(
    ma_de_thi: int = Form(...),
    ma_lop: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """
    Tải ảnh phiếu trả lời lên hệ thống:
    1. Chạy OMR Engine phát hiện SBD, Mã đề và Đáp án
    2. So khớp cơ sở dữ liệu để tìm Học sinh và Mã đề tương ứng
    3. Tự động chấm điểm và cảnh báo nếu có ô bất thường
    """
    de_thi = db.query(DeThi).filter(DeThi.MaDeThi == ma_de_thi).first()
    if not de_thi:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề thi.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Tệp ảnh tải lên trống.")

    # Execute OMR Engine
    try:
        omr_result = omr_engine.process_sheet(contents, so_cau_hoi=de_thi.SoCau)
    except Exception as e:
        # Nếu OpenCV không xử lý được
        phieu_err = PhieuTraLoi(
            MaDeThi=ma_de_thi,
            MaLop=ma_lop,
            MaNguoiDung=user.MaNguoiDung,
            DuongDanAnhGoc=f"storage/phieu_{file.filename}",
            TrangThai=TrangThaiPhieuEnum.XU_LY_LOI
        )
        db.add(phieu_err)
        db.commit()
        raise HTTPException(status_code=400, detail=f"Không thể xử lý ảnh phiếu: {str(e)}")

    # Tìm mã đề từ số hiệu mã đề OMR phát hiện được
    recognized_md_str = omr_result["ma_de"]
    ma_de_obj = db.query(MaDe).filter(
        MaDe.MaDeThi == ma_de_thi,
        MaDe.SoHieuMaDe == recognized_md_str
    ).first()

    # Tìm học sinh từ SBD OMR phát hiện được
    recognized_sbd = omr_result["so_bao_danh"]
    hoc_sinh_obj = None
    if ma_lop:
        hoc_sinh_obj = db.query(HocSinh).filter(
            HocSinh.MaLop == ma_lop,
            HocSinh.SoBaoDanh == recognized_sbd
        ).first()

    # Xác định trạng thái ban đầu
    has_anomaly = omr_result["has_any_abnormal"] or (not ma_de_obj) or (not hoc_sinh_obj)
    trang_thai_init = TrangThaiPhieuEnum.CAN_XEM_LAI if has_anomaly else TrangThaiPhieuEnum.DA_CHAM_XONG

    phieu = PhieuTraLoi(
        MaDeThi=ma_de_thi,
        MaHocSinh=hoc_sinh_obj.MaHocSinh if hoc_sinh_obj else None,
        MaMaDe=ma_de_obj.MaMaDe if ma_de_obj else None,
        MaLop=ma_lop,
        MaNguoiDung=user.MaNguoiDung,
        DuongDanAnhGoc=f"storage/phieu_{file.filename}",
        TrangThai=trang_thai_init
    )
    db.add(phieu)
    db.flush()

    # Lưu chi tiết bài làm
    cau_hoi_in_exam = (
        db.query(DeThi_CauHoi)
        .filter(DeThi_CauHoi.MaDeThi == ma_de_thi)
        .order_by(DeThi_CauHoi.SoThuTuGoc)
        .all()
    )

    # Nếu tìm thấy mã đề và có ánh xạ thứ tự câu hỏi hoán vị
    thu_tu_map = ma_de_obj.ThuTuCauHoi_JSON if (ma_de_obj and ma_de_obj.ThuTuCauHoi_JSON) else {}

    for idx in range(1, de_thi.SoCau + 1):
        dt_ch_id = thu_tu_map.get(str(idx))
        if not dt_ch_id and idx <= len(cau_hoi_in_exam):
            dt_ch_id = cau_hoi_in_exam[idx - 1].MaDeThiCauHoi

        if not dt_ch_id:
            continue

        ans = omr_result["dap_an_da_chon"].get(idx)
        conf = omr_result["do_tin_cay"].get(idx, 1.0)
        abnormal = omr_result["co_bat_thuong"].get(idx, False)

        dt_bl = ChiTietBaiLam(
            MaPhieu=phieu.MaPhieu,
            MaDeThiCauHoi=dt_ch_id,
            DapAnDaChon=ans,
            DoTinCay=conf,
            CoBatThuong=abnormal
        )
        db.add(dt_bl)

    db.commit()

    # Tính điểm
    _recalculate_score(db, phieu)
    db.refresh(phieu)

    return phieu


@router.get("/phieu", response_model=List[PhieuTraLoiResponse])
def get_danh_sach_phieu(
    ma_de_thi: Optional[int] = Query(None),
    ma_lop: Optional[int] = Query(None),
    trang_thai: Optional[TrangThaiPhieuEnum] = Query(None),
    skip: int = Query(0, ge=0, description="Số bản ghi bỏ qua"),
    limit: int = Query(50, ge=1, le=200, description="Số bản ghi tối đa"),
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Lấy danh sách phiếu trả lời đã chụp/chấm."""
    query = (
        db.query(PhieuTraLoi)
        .options(
            joinedload(PhieuTraLoi.hoc_sinh),
            joinedload(PhieuTraLoi.ma_de),
            joinedload(PhieuTraLoi.lop),
            joinedload(PhieuTraLoi.ket_qua),
        )
        .filter(PhieuTraLoi.MaNguoiDung == user.MaNguoiDung)
    )
    if ma_de_thi:
        query = query.filter(PhieuTraLoi.MaDeThi == ma_de_thi)
    if ma_lop:
        query = query.filter(PhieuTraLoi.MaLop == ma_lop)
    if trang_thai:
        query = query.filter(PhieuTraLoi.TrangThai == trang_thai)
    return query.offset(skip).limit(limit).all()


@router.get("/phieu/{ma_phieu}", response_model=PhieuTraLoiDetailResponse)
def get_chi_tiet_phieu(
    ma_phieu: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Xem chi tiết phiếu trả lời, đáp án từng câu và điểm số."""
    phieu = db.query(PhieuTraLoi).filter(
        PhieuTraLoi.MaPhieu == ma_phieu,
        PhieuTraLoi.MaNguoiDung == user.MaNguoiDung
    ).first()
    if not phieu:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu trả lời.")
    return phieu


@router.put("/phieu/{ma_phieu}/sua-tay", response_model=PhieuTraLoiDetailResponse)
def sua_tay_ket_qua(
    ma_phieu: int,
    payload: CapNhatBaiLamRequest,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """
    Giáo viên điều chỉnh đáp án ô mờ hoặc gán lại Mã đề / Học sinh (GV-07).
    Hệ thống tự động cập nhật lại điểm số ngay lập tức!
    """
    phieu = db.query(PhieuTraLoi).filter(
        PhieuTraLoi.MaPhieu == ma_phieu,
        PhieuTraLoi.MaNguoiDung == user.MaNguoiDung
    ).first()
    if not phieu:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu trả lời.")

    if payload.MaHocSinh:
        phieu.MaHocSinh = payload.MaHocSinh
    if payload.MaMaDe:
        phieu.MaMaDe = payload.MaMaDe

    if payload.dap_an_dieu_chinh:
        for item in payload.dap_an_dieu_chinh:
            dt = db.query(ChiTietBaiLam).filter(
                ChiTietBaiLam.MaPhieu == ma_phieu,
                ChiTietBaiLam.MaDeThiCauHoi == item.MaDeThiCauHoi
            ).first()
            if dt:
                dt.DapAnDaChon = item.DapAnMoi
                dt.CoBatThuong = False  # Đã được GV xác nhận sửa

    phieu.TrangThai = TrangThaiPhieuEnum.DA_CHINH_SUA
    db.commit()

    # Recalculate score
    kq = _recalculate_score(db, phieu)
    kq.DaChinhSuaThuCong = True  # type: ignore[assignment]
    db.commit()
    db.refresh(phieu)
    return phieu


@router.post("/phieu/{ma_phieu}/chot-luu", response_model=PhieuTraLoiResponse)
def chot_luu_ket_qua(
    ma_phieu: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Chốt kết quả chấm bài chính thức (chuyển sang trạng thái DA_LUU)."""
    phieu = db.query(PhieuTraLoi).filter(
        PhieuTraLoi.MaPhieu == ma_phieu,
        PhieuTraLoi.MaNguoiDung == user.MaNguoiDung
    ).first()
    if not phieu:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu trả lời.")

    if not phieu.MaHocSinh or not phieu.MaMaDe:
        raise HTTPException(
            status_code=400,
            detail="Vui lòng gán đầy đủ Mã Học Sinh và Mã Đề Thi trước khi chốt lưu kết quả."
        )

    phieu.TrangThai = TrangThaiPhieuEnum.DA_LUU
    db.commit()
    db.refresh(phieu)
    return phieu
