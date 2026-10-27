"""
main.py — Điểm khởi đầu ứng dụng FastAPI
Cấu hình: CORS, API docs, startup events, exception handlers
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo database tables khi khởi động
    from app.core.database import engine, Base
    import app.models  # Import tất cả ORM models để metadata nhận diện đầy đủ các bảng
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        description="""
## Hệ thống Chấm bài Trắc nghiệm bằng Ảnh chụp

API backend phục vụ:
- **App Flutter** dành cho giáo viên (chụp ảnh, chấm điểm)
- **Trang Admin React** dành cho quản trị viên (duyệt tài khoản, câu hỏi)

### Xác thực
Sử dụng **JWT Bearer Token**. Đăng nhập tại `/api/v1/auth/login` để lấy token.
Token có hiệu lực **24 giờ**.
        """,
        docs_url="/docs" if settings.DEBUG else None,   # Ẩn Swagger khi production
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
    )

    # ── CORS Middleware ─────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routes ──────────────────────────────────────────────────────────
    app.include_router(api_router)
  
    # ── Health check (không cần auth) ───────────────────────────────────────
    @app.get("/health", tags=["System"])
    def health_check():
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    # ── Root ────────────────────────────────────────────────────────────────
    @app.get("/", tags=["System"])
    def root():
        return {
            "message": f"Chào mừng đến với {settings.APP_NAME}",
            "docs": "/docs" if settings.DEBUG else "API docs bị ẩn ở môi trường production",
            "health": "/health",
        }

    # ── Global Exception Handler ────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        if settings.DEBUG:
            raise exc  # Re-raise để thấy traceback đầy đủ khi dev
        return JSONResponse(
            status_code=500,
            content={"detail": "Lỗi hệ thống nội bộ. Vui lòng thử lại sau."},
        )

    return app


app = create_app()
