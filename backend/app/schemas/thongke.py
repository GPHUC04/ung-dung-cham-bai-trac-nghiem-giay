"""
schemas/thongke.py — Pydantic schemas cho Báo cáo Thống kê (GV-09, AD-07)
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, ConfigDict


class PhoDiemItem(BaseModel):
    KhoangDiem: str  # VD: "0.0 - 1.0", "1.0 - 2.0" ... "9.0 - 10.0"
    SoLuong: int


class ThongKeLopResponse(BaseModel):
    MaLop: Optional[int] = None
    TenLop: Optional[str] = "Tất cả các lớp"
    MaDeThi: int
    TenDeThi: str
    TongSoPhieu: int
    DiemTrungBinh: float
    DiemCaoNhat: float
    DiemThapNhat: float
    TiLeGioi: float   # Điểm >= 8.0 (%)
    TiLeKha: float    # 6.5 <= Điểm < 8.0 (%)
    TiLeTrungBinh: float  # 5.0 <= Điểm < 6.5 (%)
    TiLeYeu: float    # Điểm < 5.0 (%)
    PhoDiem: List[PhoDiemItem] = []


class ThongKeCauHoiItem(BaseModel):
    MaDeThiCauHoi: int
    SoThuTuGoc: int
    NoiDungCauHoi: str
    SoLuotLam: int
    SoLuotDung: int
    TiLeDung: float  # % (Độ khó thực tế)
    DoPhanBiet: Optional[float] = None
    PhanBoiDapAn: Dict[str, int] = {}  # {"A": 12, "B": 4, "C": 2, "D": 1}
