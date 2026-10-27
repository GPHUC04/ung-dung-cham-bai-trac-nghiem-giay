"""
schemas/danhmuc.py — Pydantic schemas cho Danh mục chung & Chủ đề (AD-03, GV-13)
"""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.danhmuc import LoaiDanhMucEnum


# --- DanhMucChung ---
class DanhMucChungBase(BaseModel):
    LoaiDanhMuc: LoaiDanhMucEnum
    TenDanhMuc: str


class DanhMucChungCreate(DanhMucChungBase):
    pass


class DanhMucChungUpdate(BaseModel):
    TenDanhMuc: Optional[str] = None


class DanhMucChungResponse(DanhMucChungBase):
    MaDanhMuc: int

    model_config = ConfigDict(from_attributes=True)


# --- ChuDe ---
class ChuDeBase(BaseModel):
    TenChuDe: str
    MaDanhMuc: int  # Môn học
    MaChuDeCha: Optional[int] = None  # NULL nếu là chương, có ID nếu là bài con


class ChuDeCreate(ChuDeBase):
    pass


class ChuDeUpdate(BaseModel):
    TenChuDe: Optional[str] = None
    MaChuDeCha: Optional[int] = None


class ChuDeResponse(ChuDeBase):
    MaChuDe: int
    chu_de_con: List["ChuDeResponse"] = []

    model_config = ConfigDict(from_attributes=True)
