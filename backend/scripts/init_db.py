# Script khởi tạo database — tạo admin mặc định và dữ liệu mẫu
# Chạy sau khi đã chạy: alembic upgrade head
"""
scripts/init_db.py — Seed dữ liệu khởi tạo
Tạo:
  1. Tài khoản admin mặc định (nếu chưa có)
  2. Danh mục môn học, khối lớp, năm học cơ bản

Chạy: 
  cd backend
  source venv/bin/activate
  python scripts/init_db.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.nguoidung import NguoiDung, VaiTroEnum, TrangThaiTaiKhoanEnum
from app.models.danhmuc import DanhMucChung, LoaiDanhMucEnum


def seed_admin(db):
    """Tạo tài khoản admin mặc định nếu chưa có"""
    existing = db.query(NguoiDung).filter(
        NguoiDung.VaiTro == VaiTroEnum.QUAN_TRI
    ).first()
    if existing:
        print(f"  ✅ Admin đã tồn tại: {existing.TenDangNhap}")
        return

    admin = NguoiDung(
        HoTen="Quản trị viên",
        TenDangNhap="admin",
        MatKhau_Hash=hash_password("Admin@123456"),  # ĐỔI MẬT KHẨU SAU KHI DEPLOY
        VaiTro=VaiTroEnum.QUAN_TRI,
        TrangThaiTaiKhoan=TrangThaiTaiKhoanEnum.DA_KICH_HOAT,
        Email="admin@school.edu.vn",
    )
    db.add(admin)
    print("  ✅ Tạo tài khoản admin mặc định: admin / Admin@123456")
    print("  ⚠️  HÃY ĐỔI MẬT KHẨU NGAY SAU KHI ĐĂNG NHẬP LẦN ĐẦU!")


def seed_danh_muc(db):
    """Tạo danh mục môn học, khối lớp, năm học cơ bản"""
    # Kiểm tra đã seed chưa
    if db.query(DanhMucChung).count() > 0:
        print(f"  ✅ Danh mục đã có sẵn ({db.query(DanhMucChung).count()} bản ghi)")
        return

    mon_hoc = [
        "Toán", "Vật lý", "Hóa học", "Sinh học",
        "Ngữ văn", "Lịch sử", "Địa lý", "GDCD",
        "Tiếng Anh", "Tin học",
    ]
    khoi_lop = ["Khối 10", "Khối 11", "Khối 12"]
    nam_hoc = ["2024-2025", "2025-2026", "2026-2027"]

    for ten in mon_hoc:
        db.add(DanhMucChung(LoaiDanhMuc=LoaiDanhMucEnum.MON_HOC, TenDanhMuc=ten))

    for ten in khoi_lop:
        db.add(DanhMucChung(LoaiDanhMuc=LoaiDanhMucEnum.KHOI_LOP, TenDanhMuc=ten))

    for ten in nam_hoc:
        db.add(DanhMucChung(LoaiDanhMuc=LoaiDanhMucEnum.NAM_HOC, TenDanhMuc=ten))

    print(f"  ✅ Tạo {len(mon_hoc)} môn học, {len(khoi_lop)} khối lớp, {len(nam_hoc)} năm học")


def main():
    print("\n🚀 Khởi tạo database...")
    db = SessionLocal()
    try:
        print("\n[1/2] Tạo tài khoản admin:")
        seed_admin(db)

        print("\n[2/2] Tạo danh mục dùng chung:")
        seed_danh_muc(db)

        db.commit()
        print("\n✅ Hoàn thành! Database sẵn sàng sử dụng.\n")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Lỗi: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
