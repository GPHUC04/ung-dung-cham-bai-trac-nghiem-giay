"""
api/v1/nganhang.py — API Ngân hàng câu hỏi & Duyệt câu hỏi (GV-13, AD-02)
Endpoints:
- GET  /nganhang/cau-hoi              — Tìm kiếm / lọc câu hỏi
- POST /nganhang/cau-hoi              — Tạo câu hỏi mới (đáp án A/B/C/D, tags, ảnh)
- GET  /nganhang/cau-hoi/{id}         — Chi tiết câu hỏi
- PUT  /nganhang/cau-hoi/{id}         — Cập nhật câu hỏi (kiểm tra bất biến dữ liệu)
- POST /nganhang/cau-hoi/{id}/gui-duyet — Gửi đề xuất đưa vào kho chung
- POST /nganhang/cau-hoi/{id}/duyet   — [Admin] Phê duyệt/Từ chối vào kho chung
- DELETE /nganhang/cau-hoi/{id}       — Xóa câu hỏi
"""
from typing import List, Optional
from datetime import datetime , timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_


from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_giao_vien, require_quan_tri
from app.models.nguoidung import NguoiDung, VaiTroEnum
from app.models.nganhang import (
    CauHoiNganHang, LuaChonCauHoi, TuKhoa, CauHoiNH_TuKhoa,
    TepDinhKemCauHoi, LichSuChinhSuaCauHoi,
    MucDoNhanThucEnum, TrangThaiDuyetEnum, ChuDe
)
from app.schemas.nganhang import (
    CauHoiCreate, CauHoiUpdate, CauHoiResponse, CauHoiDuyetRequest
)

router = APIRouter(prefix="/nganhang", tags=["Ngân hàng câu hỏi"])


@router.get("/cau-hoi", response_model=List[CauHoiResponse])
def get_danh_sach_cau_hoi(
    ma_chu_de: Optional[int] = Query(None, description="Lọc theo chủ đề"),
    muc_do: Optional[MucDoNhanThucEnum] = Query(None, description="Nhận biết, Thông hiểu..."),
    trang_thai: Optional[TrangThaiDuyetEnum] = Query(None, description="Trạng thái duyệt"),
    search: Optional[str] = Query(None, description="Tìm kiếm từ khóa trong nội dung câu hỏi"),
    kho_chung_only: bool = Query(False, description="Chỉ lấy các câu hỏi đã được Admin duyệt vào kho chung"),
    skip: int = Query(0, ge=0, description="Số bản ghi bỏ qua (phân trang)"),
    limit: int = Query(50, ge=1, le=200, description="Số bản ghi tối đa trả về"),
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(get_current_user)
):
    """Lấy danh sách câu hỏi trong ngân hàng với bộ lọc phong phú."""
    query = db.query(CauHoiNganHang)

    if kho_chung_only:
        query = query.filter(CauHoiNganHang.TrangThaiDuyet == TrangThaiDuyetEnum.DA_DUYET)
    elif user.VaiTro != VaiTroEnum.QUAN_TRI:
        # Giáo viên xem câu hỏi của chính mình HOẶC các câu đã duyệt trong kho chung
        query = query.filter(
            or_(
                CauHoiNganHang.MaNguoiDung == user.MaNguoiDung,
                CauHoiNganHang.TrangThaiDuyet == TrangThaiDuyetEnum.DA_DUYET
            )
        )

    if ma_chu_de:
        query = query.filter(CauHoiNganHang.MaChuDe == ma_chu_de)
    if muc_do:
        query = query.filter(CauHoiNganHang.MucDoNhanThuc == muc_do)
    if trang_thai:
        query = query.filter(CauHoiNganHang.TrangThaiDuyet == trang_thai)
    if search:
        query = query.filter(CauHoiNganHang.NoiDungCauHoi.ilike(f"%{search}%"))

    return query.offset(skip).limit(limit).all()


@router.post("/cau-hoi", response_model=CauHoiResponse, status_code=status.HTTP_201_CREATED)
def create_cau_hoi(
    payload: CauHoiCreate,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Tạo câu hỏi mới kèm phương án A/B/C/D và tags."""
    chu_de = db.query(ChuDe).filter(ChuDe.MaChuDe == payload.MaChuDe).first()
    if not chu_de:
        raise HTTPException(status_code=400, detail="Chủ đề không tồn tại.")

    # Must have at least 1 correct answer
    has_correct = any(opt.LaDapAnDung for opt in payload.lua_chon)
    if not has_correct:
        raise HTTPException(status_code=400, detail="Câu hỏi phải có ít nhất 1 đáp án đúng.")

    cau_hoi = CauHoiNganHang(
        NoiDungCauHoi=payload.NoiDungCauHoi,
        MaChuDe=payload.MaChuDe,
        MucDoNhanThuc=payload.MucDoNhanThuc,
        TrangThaiDuyet=TrangThaiDuyetEnum.NHAP,
        MaNguoiDung=user.MaNguoiDung,
        SoLanSuDung=0
    )
    db.add(cau_hoi)
    db.flush()  # Get generated MaCauHoiNH

    # Add options A/B/C/D
    for opt in payload.lua_chon:
        lua_chon = LuaChonCauHoi(
            MaCauHoiNH=cau_hoi.MaCauHoiNH,
            NoiDungLuaChon=opt.NoiDungLuaChon,
            LaDapAnDung=opt.LaDapAnDung,
            ThuTuHienThi=opt.ThuTuHienThi
        )
        db.add(lua_chon)

    # Process tags (TuKhoa)
    if payload.tu_khoa:
        for tag_name in payload.tu_khoa:
            tag_name_clean = tag_name.strip().lower()
            tag = db.query(TuKhoa).filter(TuKhoa.TenTuKhoa == tag_name_clean).first()
            if not tag:
                tag = TuKhoa(TenTuKhoa=tag_name_clean)
                db.add(tag)
                db.flush()
            link = CauHoiNH_TuKhoa(MaCauHoiNH=cau_hoi.MaCauHoiNH, MaTuKhoa=tag.MaTuKhoa)
            db.add(link)

    # Process attachments
    if payload.tep_dinh_kem:
        for att in payload.tep_dinh_kem:
            tep = TepDinhKemCauHoi(
                MaCauHoiNH=cau_hoi.MaCauHoiNH,
                DuongDan=att.DuongDan,
                LoaiTep=att.LoaiTep
            )
            db.add(tep)

    db.commit()
    db.refresh(cau_hoi)
    return cau_hoi


@router.get("/cau-hoi/{ma_cau_hoi}", response_model=CauHoiResponse)
def get_chi_tiet_cau_hoi(
    ma_cau_hoi: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(get_current_user)
):
    """Chi tiết một câu hỏi."""
    q = db.query(CauHoiNganHang).filter(CauHoiNganHang.MaCauHoiNH == ma_cau_hoi).first()
    if not q:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")
    return q


@router.put("/cau-hoi/{ma_cau_hoi}", response_model=CauHoiResponse)
def update_cau_hoi(
    ma_cau_hoi: int,
    payload: CauHoiUpdate,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """
    Cập nhật câu hỏi.
    QUY TẮC BẤT BIẾN:
    Nếu SoLanSuDung > 0, hệ thống tự động ghi nhật ký sửa đổi vào LichSuChinhSuaCauHoi
    trước khi cập nhật để bảo toàn lịch sử chấm bài.
    """
    q = db.query(CauHoiNganHang).filter(CauHoiNganHang.MaCauHoiNH == ma_cau_hoi).first()
    if not q:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")

    if q.MaNguoiDung != user.MaNguoiDung and user.VaiTro != VaiTroEnum.QUAN_TRI:
        raise HTTPException(status_code=403, detail="Bạn không có quyền sửa câu hỏi này.")

    # Save audit diff if used in existing exams
    if q.SoLanSuDung > 0:
        diff = {
            "NoiDungCauHoi_old": q.NoiDungCauHoi,
            "MucDoNhanThuc_old": q.MucDoNhanThuc.value if q.MucDoNhanThuc else None,
            "NgaySua": datetime.now(timezone.utc).isoformat()
        }
        history = LichSuChinhSuaCauHoi(
            MaCauHoiNH=q.MaCauHoiNH,
            MaNguoiDung=user.MaNguoiDung,
            NoiDungTruoc=diff
        )
        db.add(history)

    if payload.NoiDungCauHoi:
        q.NoiDungCauHoi = payload.NoiDungCauHoi
    if payload.MaChuDe:
        q.MaChuDe = payload.MaChuDe
    if payload.MucDoNhanThuc:
        q.MucDoNhanThuc = payload.MucDoNhanThuc

    # Cập nhật lựa chọn đáp án (A/B/C/D) nếu được gửi lên
    if payload.lua_chon is not None:
        # Xóa tất cả lựa chọn cũ rồi tạo lại
        db.query(LuaChonCauHoi).filter(LuaChonCauHoi.MaCauHoiNH == ma_cau_hoi).delete()
        # Phải có ít nhất 1 đáp án đúng
        has_correct = any(opt.LaDapAnDung for opt in payload.lua_chon)
        if not has_correct:
            raise HTTPException(status_code=400, detail="Câu hỏi phải có ít nhất 1 đáp án đúng.")
        for opt in payload.lua_chon:
            db.add(LuaChonCauHoi(
                MaCauHoiNH=q.MaCauHoiNH,
                NoiDungLuaChon=opt.NoiDungLuaChon,
                LaDapAnDung=opt.LaDapAnDung,
                ThuTuHienThi=opt.ThuTuHienThi
            ))

    # Cập nhật từ khóa nếu được gửi lên
    if payload.tu_khoa is not None:
        # Xóa liên kết từ khóa cũ
        db.query(CauHoiNH_TuKhoa).filter(CauHoiNH_TuKhoa.MaCauHoiNH == ma_cau_hoi).delete()
        for tag_name in payload.tu_khoa:
            tag_name_clean = tag_name.strip().lower()
            if not tag_name_clean:
                continue
            tag = db.query(TuKhoa).filter(TuKhoa.TenTuKhoa == tag_name_clean).first()
            if not tag:
                tag = TuKhoa(TenTuKhoa=tag_name_clean)
                db.add(tag)
                db.flush()
            db.add(CauHoiNH_TuKhoa(MaCauHoiNH=q.MaCauHoiNH, MaTuKhoa=tag.MaTuKhoa))

    q.NgayCapNhat = datetime.now(timezone.utc)
    db.commit()
    db.refresh(q)
    return q


@router.post("/cau-hoi/{ma_cau_hoi}/gui-duyet", response_model=CauHoiResponse)
def gui_duyet_cau_hoi(
    ma_cau_hoi: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Giáo viên đề xuất đưa câu hỏi vào Kho dùng chung (GV-13)."""
    q = db.query(CauHoiNganHang).filter(CauHoiNganHang.MaCauHoiNH == ma_cau_hoi).first()
    if not q:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")
    if q.MaNguoiDung != user.MaNguoiDung:
        raise HTTPException(status_code=403, detail="Chỉ tác giả mới có quyền gửi duyệt.")

    q.TrangThaiDuyet = TrangThaiDuyetEnum.CHO_DUYET
    db.commit()
    db.refresh(q)
    return q


@router.post("/cau-hoi/{ma_cau_hoi}/duyet", response_model=CauHoiResponse)
def duyet_cau_hoi(
    ma_cau_hoi: int,
    payload: CauHoiDuyetRequest,
    db: Session = Depends(get_db),
    admin: NguoiDung = Depends(require_quan_tri)
):
    """Quản trị viên phê duyệt hoặc từ chối câu hỏi đưa vào Kho chung (AD-02)."""
    q = db.query(CauHoiNganHang).filter(CauHoiNganHang.MaCauHoiNH == ma_cau_hoi).first()
    if not q:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")

    if payload.TrangThaiDuyet not in [TrangThaiDuyetEnum.DA_DUYET, TrangThaiDuyetEnum.TU_CHOI]:
        raise HTTPException(status_code=400, detail="Trạng thái phê duyệt không hợp lệ.")

    q.TrangThaiDuyet = payload.TrangThaiDuyet
    db.commit()
    db.refresh(q)
    return q


@router.delete("/cau-hoi/{ma_cau_hoi}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cau_hoi(
    ma_cau_hoi: int,
    db: Session = Depends(get_db),
    user: NguoiDung = Depends(require_giao_vien)
):
    """Xóa câu hỏi khỏi ngân hàng (nếu chưa được sử dụng)."""
    q = db.query(CauHoiNganHang).filter(CauHoiNganHang.MaCauHoiNH == ma_cau_hoi).first()
    if not q:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")

    if q.SoLanSuDung > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể xóa câu hỏi đã được đưa vào {q.SoLanSuDung} đề thi."
        )

    db.delete(q)
    db.commit()
