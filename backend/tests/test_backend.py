import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.nguoidung import NguoiDung, VaiTroEnum
from app.core.security import create_access_token

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def auth_tokens(db):
    admin = db.query(NguoiDung).filter(NguoiDung.VaiTro == VaiTroEnum.QUAN_TRI).first()
    gv = db.query(NguoiDung).filter(NguoiDung.VaiTro == VaiTroEnum.GIAO_VIEN).first()
    
    admin_token = create_access_token({"sub": str(admin.MaNguoiDung), "role": admin.VaiTro.value}) if admin else ""
    gv_token = create_access_token({"sub": str(gv.MaNguoiDung), "role": gv.VaiTro.value}) if gv else ""
    
    return {
        "admin": {"Authorization": f"Bearer {admin_token}"},
        "gv": {"Authorization": f"Bearer {gv_token}"}
    }


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_root():
    res = client.get("/")
    assert res.status_code == 200
    assert "message" in res.json()


def test_auth_me(auth_tokens):
    res = client.get("/api/v1/auth/me", headers=auth_tokens["gv"])
    assert res.status_code == 200
    data = res.json()
    assert data["VaiTro"] == "GIAO_VIEN"


def test_admin_tai_khoan(auth_tokens):
    res = client.get("/api/v1/admin/tai-khoan", headers=auth_tokens["admin"])
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_admin_nhat_ky(auth_tokens):
    res = client.get("/api/v1/admin/nhat-ky", headers=auth_tokens["admin"])
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_danhmuc(auth_tokens):
    res = client.get("/api/v1/danhmuc/", headers=auth_tokens["gv"])
    assert res.status_code == 200
    assert len(res.json()) > 0


def test_lophoc_list(auth_tokens):
    res = client.get("/api/v1/lophoc/", headers=auth_tokens["gv"])
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_nganhang_cauhoi(auth_tokens):
    res = client.get("/api/v1/nganhang/cau-hoi", headers=auth_tokens["gv"])
    assert res.status_code == 200
    assert len(res.json()) > 0


def test_dethi_detail_and_ma_de(auth_tokens):
    res = client.get("/api/v1/dethi/1", headers=auth_tokens["gv"])
    assert res.status_code == 200
    data = res.json()
    assert data["MaDeThi"] == 1
    assert "ma_de_list" in data
    assert len(data["ma_de_list"]) > 0
    # Kiểm tra mỗi mã đề có danh sách đáp án đúng kèm SoThuTuMoi
    first_ma_de = data["ma_de_list"][0]
    assert len(first_ma_de["dap_an_dung"]) > 0
    assert first_ma_de["dap_an_dung"][0]["SoThuTuMoi"] is not None


def test_ma_tran_dap_an(auth_tokens):
    res = client.get("/api/v1/dethi/1/ma-tran-dap-an", headers=auth_tokens["gv"])
    assert res.status_code == 200
    data = res.json()
    assert "Matrix" in data
    assert len(data["Matrix"]) == 20


def test_chambai_list(auth_tokens):
    res = client.get("/api/v1/chambai/phieu", headers=auth_tokens["gv"])
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_thongke_lop(auth_tokens):
    res = client.get("/api/v1/thongke/dethi/1/lop", headers=auth_tokens["gv"])
    assert res.status_code == 200
    data = res.json()
    assert data["MaDeThi"] == 1


def test_export_excel(auth_tokens):
    res = client.get("/api/v1/thongke/dethi/1/export/excel", headers=auth_tokens["gv"])
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_export_csv(auth_tokens):
    res = client.get("/api/v1/thongke/dethi/1/export/csv", headers=auth_tokens["gv"])
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
