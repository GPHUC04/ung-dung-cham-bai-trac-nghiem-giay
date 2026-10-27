"""
scripts/seed_demo_data.py — Script Seed dữ liệu mẫu phong phú cho Hệ thống Chấm bài
Tạo sẵn:
- 1 Tài khoản Admin: admin / admin123 (Đã duyệt)
- 1 Tài khoản Giáo viên: giaovien1 / 123456 (Đã duyệt)
- Danh mục: Môn Toán, Khối 10, Năm học 2024-2025
- 1 Lớp học (10A1) + 10 Học sinh (SBD: 000101 -> 000110)
- Ngân hàng câu hỏi: 20 câu hỏi Toán (A/B/C/D)
- Đề thi gốc: "Đề thi Giữa Kỳ I Toán 10" (20 câu)
- 4 Mã đề hoán vị: 101, 102, 103, 104 + Bảng đáp án đúng tương ứng
"""
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.nguoidung import NguoiDung, VaiTroEnum, TrangThaiTaiKhoanEnum
from app.models.danhmuc import DanhMucChung, LoaiDanhMucEnum
from app.models.lophoc import Lop, HocSinh
from app.models.nganhang import ChuDe, CauHoiNganHang, LuaChonCauHoi, MucDoNhanThucEnum, TrangThaiDuyetEnum
from app.models.dethi import DeThi, DeThi_CauHoi
from app.schemas.dethi import SinhMaDeRequest
from app.services.dethi import tao_danh_sach_ma_de


def seed():
    db = SessionLocal()
    print("🌱 Bắt đầu khởi tạo dữ liệu mẫu...")

    # 1. Admin
    admin = db.query(NguoiDung).filter(NguoiDung.TenDangNhap == "admin").first()
    if not admin:
        admin = NguoiDung(
            HoTen="Quản trị viên Hệ thống",
            TenDangNhap="admin",
            MatKhau_Hash=hash_password("admin123"),
            VaiTro=VaiTroEnum.QUAN_TRI,
            TrangThaiTaiKhoan=TrangThaiTaiKhoanEnum.DA_KICH_HOAT,
            Email="admin@chamthi.edu.vn"
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print("  ✓ Tạo tài khoản Admin: admin / admin123")

    # 2. Teacher
    gv = db.query(NguoiDung).filter(NguoiDung.TenDangNhap == "giaovien1").first()
    if not gv:
        gv = NguoiDung(
            HoTen="Thầy Nguyễn Văn A",
            TenDangNhap="giaovien1",
            MatKhau_Hash=hash_password("123456"),
            VaiTro=VaiTroEnum.GIAO_VIEN,
            TrangThaiTaiKhoan=TrangThaiTaiKhoanEnum.DA_KICH_HOAT,
            Email="nguyenvana@truongthpt.edu.vn"
        )
        db.add(gv)
        db.commit()
        db.refresh(gv)
        print("  ✓ Tạo tài khoản Giáo viên: giaovien1 / 123456")

    # 3. Catalogs
    mon_toan = db.query(DanhMucChung).filter(DanhMucChung.TenDanhMuc == "Môn Toán").first()
    if not mon_toan:
        mon_toan = DanhMucChung(LoaiDanhMuc=LoaiDanhMucEnum.MON_HOC, TenDanhMuc="Môn Toán")
        db.add(mon_toan)

    khoi_10 = db.query(DanhMucChung).filter(DanhMucChung.TenDanhMuc == "Khối 10").first()
    if not khoi_10:
        khoi_10 = DanhMucChung(LoaiDanhMuc=LoaiDanhMucEnum.KHOI_LOP, TenDanhMuc="Khối 10")
        db.add(khoi_10)

    nam_hoc = db.query(DanhMucChung).filter(DanhMucChung.TenDanhMuc == "2024-2025").first()
    if not nam_hoc:
        nam_hoc = DanhMucChung(LoaiDanhMuc=LoaiDanhMucEnum.NAM_HOC, TenDanhMuc="2024-2025")
        db.add(nam_hoc)

    db.commit()
    print("  ✓ Tạo danh mục dùng chung (Môn Toán, Khối 10, 2024-2025)")

    # 4. Class & Students
    lop = db.query(Lop).filter(Lop.TenLop == "10A1", Lop.MaNguoiDung == gv.MaNguoiDung).first()
    if not lop:
        lop = Lop(TenLop="10A1", MaDanhMuc=khoi_10.MaDanhMuc, MaNguoiDung=gv.MaNguoiDung)
        db.add(lop)
        db.commit()
        db.refresh(lop)

        students_data = [
            ("Nguyễn Văn An", "000101"),
            ("Bùi Thị Bình", "000102"),
            ("Trần Văn Cường", "000103"),
            ("Lê Thị Duyên", "000104"),
            ("Phạm Hoàng Em", "000105"),
            ("Vũ Thị Phương", "000106"),
            ("Đặng Văn Giang", "000107"),
            ("Hoàng Thị Hương", "000108"),
            ("Nông Văn Hùng", "000109"),
            ("Phan Thị Trinh", "000110"),
        ]
        for name, sbd in students_data:
            hs = HocSinh(HoTen=name, SoBaoDanh=sbd, MaLop=lop.MaLop)
            db.add(hs)
        db.commit()
        print("  ✓ Tạo Lớp 10A1 + 10 học sinh mẫu")

    # 5. Topic (Chủ đề)
    chu_de = db.query(ChuDe).filter(ChuDe.TenChuDe == "Chương 1: Mệnh đề & Tập hợp").first()
    if not chu_de:
        chu_de = ChuDe(TenChuDe="Chương 1: Mệnh đề & Tập hợp", MaDanhMuc=mon_toan.MaDanhMuc)
        db.add(chu_de)
        db.commit()
        db.refresh(chu_de)

    # 6. Question Bank (20 Questions)
    q_count = db.query(CauHoiNganHang).count()
    if q_count < 20:
        for i in range(1, 21):
            q = CauHoiNganHang(
                NoiDungCauHoi=f"Câu {i}: Cho mệnh đề P(x) = x^2 - {i}x + {i} = 0. Giá trị nào của x thỏa mãn?",
                MaChuDe=chu_de.MaChuDe,
                MucDoNhanThuc=MucDoNhanThucEnum.NHAN_BIET if i <= 10 else MucDoNhanThucEnum.THONG_HIEU,
                TrangThaiDuyet=TrangThaiDuyetEnum.DA_DUYET,
                MaNguoiDung=gv.MaNguoiDung,
                SoLanSuDung=0
            )
            db.add(q)
            db.flush()

            # 4 Options A, B, C, D (Choice A is correct for odd questions, B for even)
            correct_idx = 1 if (i % 2 == 1) else 2
            for opt_i in range(1, 5):
                opt = LuaChonCauHoi(
                    MaCauHoiNH=q.MaCauHoiNH,
                    NoiDungLuaChon=f"Phương án {chr(64 + opt_i)} của câu {i}",
                    LaDapAnDung=(opt_i == correct_idx),
                    ThuTuHienThi=opt_i
                )
                db.add(opt)
        db.commit()
        print("  ✓ Tạo 20 câu hỏi trắc nghiệm Toán trong Ngân hàng câu hỏi")

    # 7. Exam & Variants
    de_thi = db.query(DeThi).filter(DeThi.TenDeThi == "Đề Thi Giữa Kỳ I Toán 10").first()
    if not de_thi:
        all_qs = db.query(CauHoiNganHang).limit(20).all()
        de_thi = DeThi(
            TenDeThi="Đề Thi Giữa Kỳ I Toán 10",
            MaDanhMuc=mon_toan.MaDanhMuc,
            SoCau=len(all_qs),
            SoLuaChon=4,
            MaNguoiDung=gv.MaNguoiDung
        )
        db.add(de_thi)
        db.flush()

        for idx, q in enumerate(all_qs, start=1):
            dt_ch = DeThi_CauHoi(MaDeThi=de_thi.MaDeThi, MaCauHoiNH=q.MaCauHoiNH, SoThuTuGoc=idx)
            db.add(dt_ch)
        db.commit()

        # Generate 4 shuffled variants (101, 102, 103, 104)
        req = SinhMaDeRequest(so_luong_ma_de=4, tien_to_ma_de="10", xao_cau_hoi=True, xao_dap_an=True)
        tao_danh_sach_ma_de(db, de_thi, req)
        print("  ✓ Tạo Đề thi gốc + Sinh 4 Mã đề hoán vị (101, 102, 103, 104) kèm Đáp án đúng")

    db.close()
    print("🎉 Dữ liệu mẫu đã được sinh hoàn tất!")


if __name__ == "__main__":
    seed()
