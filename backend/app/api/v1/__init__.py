"""
api/v1/__init__.py — Router tổng hợp cho API v1
Tập hợp tất cả các sub-router vào một prefix chung /api/v1
"""
from fastapi import APIRouter
from app.api.v1 import auth, admin, danhmuc, lophoc, nganhang, dethi, chambai, thongke

api_router = APIRouter(prefix="/api/v1")

# Đăng ký các sub-routers
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(danhmuc.router)
api_router.include_router(lophoc.router)
api_router.include_router(nganhang.router)
api_router.include_router(dethi.router)
api_router.include_router(chambai.router)
api_router.include_router(thongke.router)




