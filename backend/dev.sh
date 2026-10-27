#!/bin/bash
# dev.sh — Script khởi động môi trường dev nhanh
# Chạy: chmod +x dev.sh && ./dev.sh

set -e

echo ""
echo "════════════════════════════════════════"
echo "  🚀 Khởi động Backend Dev Server"
echo "════════════════════════════════════════"

# Kiểm tra venv
if [ ! -d "venv" ]; then
    echo "📦 Tạo virtual environment..."
    python3 -m venv venv
fi

# Kích hoạt venv
source venv/bin/activate

# Kiểm tra .env
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  Chưa có file .env!"
    echo "   Sao chép .env.example thành .env và điền credentials:"
    echo "   cp .env.example .env"
    echo ""
    echo "   Cần điền:"
    echo "   - DATABASE_URL (từ Supabase Dashboard)"
    echo "   - SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY"
    echo "   - SECRET_KEY (tạo bằng: python3 -c \"import secrets; print(secrets.token_hex(32))\")"
    echo ""
    exit 1
fi

# Cài dependencies nếu chưa có
pip install --quiet -r requirements.txt

echo ""
echo "📋 Thông tin:"
echo "   API:      http://localhost:8000"
echo "   Swagger:  http://localhost:8000/docs"
echo "   ReDoc:    http://localhost:8000/redoc"
echo "   Health:   http://localhost:8000/health"
echo ""

# Khởi động uvicorn với hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
