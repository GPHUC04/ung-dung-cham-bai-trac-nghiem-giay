# 📝 Hệ thống Chấm bài Trắc nghiệm Giấy bằng Ảnh chụp (OMR Exam Grader)

Hệ thống chấm bài thi trắc nghiệm tự động qua ảnh chụp ứng dụng thị giác máy tính (**OpenCV / OMR**), hỗ trợ giáo viên chấm bài nhanh chóng, chính xác bằng điện thoại thông minh, đồng thời cung cấp giao diện quản trị toàn diện cho nhà trường.

---

## 📌 Mục lục

- [Giới thiệu tổng quan](#-giới-thiệu-tổng-quan)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Cấu trúc thư mục dự án](#-cấu-trúc-thư-mục-dự-án)
- [Các tính năng chính](#-các-tính-năng-chính)
  - [Nhóm chức năng Giáo viên (GV)](#nhóm-chức-năng-giáo-viên-gv)
  - [Nhóm chức năng Quản trị hệ thống (AD)](#nhóm-chức-năng-quản-trị-hệ-thống-ad)
- [Công nghệ sử dụng](#-công-nghệ-sử-dụng)
- [Yêu cầu môi trường](#-yêu-cầu-môi-trường)
- [Hướng dẫn cài đặt & Khởi chạy](#-hướng-dẫn-cài-đặt--khởi-chạy)
  - [1. Cấu hình Backend](#1-cấu-hình-backend)
  - [2. Khởi tạo Cơ sở dữ liệu & Dữ liệu mẫu](#2-khởi-tạo-cơ-sở-dữ-liệu--dữ-liệu-mẫu)
  - [3. Khởi chạy Backend Server](#3-khởi-chạy-backend-server)
  - [4. Kiểm thử (Testing)](#4-kiểm-thử-testing)
- [Tài khoản demo sẵn có](#-tài-khoản-demo-sẵn-có)
- [Danh sách API Endpoints chính](#-danh-sách-api-endpoints-chính)
- [Quy trình xử lý ảnh OMR (Core Engine)](#-quy-trình-xử-lý-ảnh-omr-core-engine)
- [Tài liệu tham khảo & Đặc tả](#-tài-liệu-tham-khảo--đặc-tả)

---

## 🌟 Giới thiệu tổng quan

Dự án được xây dựng nhằm giải quyết bài toán chấm bài trắc nghiệm truyền thống tốn nhiều thời gian và dễ xảy ra sai sót. Hệ thống bao gồm:
1. **Core Backend & OMR Engine (FastAPI + OpenCV)**: Tiếp nhận ảnh chụp phiếu làm bài, nắn chỉnh góc nghiêng (Perspective Transform), nhận diện mã đề, số báo danh, quét đáp án học sinh và tự động tính điểm theo ma trận đáp án.
2. **Mobile App (Flutter)**: Ứng dụng di động dành cho Giáo viên để chụp ảnh phiếu trả lời trực tiếp hoặc tải từ thư viện, xem kết quả, chỉnh sửa thủ công ô tô mờ/lỗi và quản lý lớp học.
3. **Admin Web (React/Vite)**: Cổng thông tin dành cho Quản trị viên quản lý danh mục, phê duyệt tài khoản giáo viên, ngân hàng câu hỏi dùng chung, thống kê và xuất báo cáo.

---

## 🏗 Kiến trúc hệ thống

```mermaid
flowchart TD
    subgraph Client["📱 Giao diện người dùng"]
        Mobile["Flutter Mobile App\n(Dành cho Giáo viên)"]
        WebAdmin["React Admin Web\n(Dành cho Quản trị viên)"]
    end

    subgraph BackendGateway["⚡ Backend Services (FastAPI)"]
        API["REST API Router (/api/v1)"]
        AuthMiddleware["JWT Authentication & RBAC"]
        OMR["OMR Processing Engine\n(OpenCV + NumPy)"]
        ShuffleEngine["Đề thi & Hoán vị mã đề"]
        StatsEngine["Thống kê & Xuất Excel/CSV"]
    end

    subgraph Storage["💾 Lưu trữ & Dữ liệu"]
        DB[("PostgreSQL / SQLite\nSQLAlchemy 2.0 ORM")]
        CloudStorage[("Supabase Storage\n(Ảnh phiếu & Câu hỏi)")]
    end

    Mobile -->|Upload ảnh / Chấm bài| API
    WebAdmin -->|Quản trị / Thống kê| API
    API --> AuthMiddleware
    API --> OMR
    API --> ShuffleEngine
    API --> StatsEngine
    OMR --> DB
    ShuffleEngine --> DB
    StatsEngine --> DB
    API --> CloudStorage
```

---

## 📁 Cấu trúc thư mục dự án

```text
├── 01_Dac_ta_chuc_nang.docx     # Tài liệu đặc tả 20 use-case chi tiết (GV & AD)
├── 02_Thiet_ke_CSDL.pdf          # Sơ đồ thiết kế Cơ sở dữ liệu quan hệ
├── admin-web/                    # Frontend ứng dụng Web Admin (React/Vite)
│   └── src/
├── backend/                      # Dịch vụ Backend API (FastAPI)
│   ├── alembic/                  # Database migration scripts
│   ├── app/
│   │   ├── api/v1/               # Các API Endpoints chia theo module
│   │   │   ├── admin.py          # Quản trị tài khoản, nhật ký (AD-01, AD-05)
│   │   │   ├── auth.py           # Đăng ký, đăng nhập JWT (GV-01)
│   │   │   ├── chambai.py        # Tải ảnh, xử lý OMR, sửa tay kết quả (GV-03 -> GV-08)
│   │   │   ├── danhmuc.py        # Danh mục môn, khối, năm học, chủ đề (AD-03)
│   │   │   ├── dethi.py          # Quản lý đề thi, sinh mã đề hoán vị (GV-10, GV-11)
│   │   │   ├── lophoc.py         # Quản lý lớp, học sinh (GV-12)
│   │   │   ├── nganhang.py       # Ngân hàng câu hỏi, duyệt câu hỏi (GV-13, AD-02)
│   │   │   └── thongke.py        # Phổ điểm, độ khó câu hỏi, xuất Excel/CSV (GV-09, AD-06, AD-07)
│   │   ├── core/                 # Cấu hình Settings, Database engine, Security (JWT/Hash)
│   │   ├── models/               # SQLAlchemy ORM Models (nguoidung, lophoc, dethi, chambai, ...)
│   │   ├── schemas/              # Pydantic Schemas validate dữ liệu vào/ra
│   │   ├── services/             # Core logic: OMR Engine, tráo đề thi, thống kê & export
│   │   └── main.py               # Điểm khởi chạy ứng dụng FastAPI, cấu hình CORS & Lifespan
│   ├── scripts/
│   │   ├── init_db.py            # Tạo bảng database tự động
│   │   └── seed_demo_data.py     # Nạp dữ liệu mẫu (Admin, Giáo viên, Đề thi, Câu hỏi)
│   ├── tests/                    # Unit tests & Integration tests (Pytest)
│   ├── dev.sh                    # Script khởi động môi trường phát triển nhanh
│   ├── requirements.txt          # Danh sách thư viện Python
│   └── .env.example              # Mẫu biến môi trường
└── flutter_app/                  # Mã nguồn ứng dụng di động Flutter
    └── lib/
```

---

## 🚀 Các tính năng chính

### Nhóm chức năng Giáo viên (GV)
| Mã | Chức năng | Phân loại | Mô tả |
| :--- | :--- | :--- | :--- |
| **GV-01** | Đăng ký / Đăng nhập | Cơ bản | Đăng ký tài khoản giáo viên (chờ duyệt) và đăng nhập bằng JWT Bearer Token |
| **GV-02** | Chọn đề thi để chấm | Cơ bản | Chọn kỳ thi, môn học và đợt thi cần thực hiện chấm |
| **GV-03** | Chụp ảnh phiếu trả lời | Cơ bản | Sử dụng camera thiết bị chụp trực tiếp phiếu làm bài trắc nghiệm |
| **GV-04** | Chọn ảnh từ thư viện | Cơ bản | Tải lên ảnh phiếu trả lời có sẵn từ album/bộ nhớ |
| **GV-05** | Xử lý chấm điểm OMR | Cơ bản | OpenCV nắn góc, định vị ô tô, nhận diện SBD, Mã đề và đáp án |
| **GV-06** | Xem kết quả chi tiết | Cơ bản | Hiển thị phiếu đã chấm trực quan kèm ảnh gốc, số câu đúng/sai/trống |
| **GV-07** | Chỉnh sửa thủ công | Nâng cao | Sửa tay các câu tô mờ, sửa lại SBD hoặc mã đề khi học sinh tô sai |
| **GV-08** | Lưu kết quả | Cơ bản | Chốt lưu kết quả bài làm vào cơ sở dữ liệu chính thức |
| **GV-09** | Xem lịch sử chấm bài | Cơ bản | Theo dõi lịch sử các đợt chấm, tra cứu bài thi của từng học sinh |
| **GV-10** | Tạo đề thi & Ma trận | Cơ bản | Tạo cấu trúc đề thi, chọn câu hỏi từ ngân hàng theo mức độ nhận thức |
| **GV-11** | Sinh mã đề hoán vị | Nâng cao | Tự động xáo trộn ngẫu nhiên thứ tự câu hỏi và đáp án A/B/C/D |
| **GV-12** | Quản lý Lớp & Học sinh | Cơ bản | Quản lý danh sách lớp học, nhập danh sách học sinh theo SBD hàng loạt |
| **GV-13** | Quản lý Ngân hàng câu hỏi | Nâng cao | Thêm/sửa câu hỏi trắc nghiệm, hình ảnh minh họa, gửi admin duyệt |

### Nhóm chức năng Quản trị hệ thống (AD)
| Mã | Chức năng | Phân loại | Mô tả |
| :--- | :--- | :--- | :--- |
| **AD-01** | Quản lý tài khoản GV | Cơ bản | Phê duyệt đăng ký tài khoản mới, khóa hoặc mở khóa tài khoản |
| **AD-02** | Quản lý kho ngân hàng | Nâng cao | Phê duyệt câu hỏi đóng góp từ giáo viên vào kho câu hỏi chung |
| **AD-03** | Quản lý danh mục chung | Cơ bản | Quản lý danh mục Khối lớp, Môn học, Năm học, Học kỳ, Chủ đề |
| **AD-04** | Quản lý phân quyền | Nâng cao | Kiểm soát vai trò Admin / Giáo viên (RBAC) |
| **AD-05** | Xem nhật ký hệ thống | Nâng cao | Ghi vết (Audit Log) các thao tác quan trọng trên hệ thống |
| **AD-06** | Xuất báo cáo điểm số | Cơ bản | Xuất bảng điểm chi tiết ra tệp **Excel (.xlsx)** hoặc **CSV** chuẩn VNEdu/SMAS |
| **AD-07** | Thống kê & Phân tích | Nâng cao | Tính phổ điểm, điểm trung bình, xếp loại và phân tích độ khó câu hỏi |

---

## 🛠 Công nghệ sử dụng

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+) - Hiệu năng cao, tự động sinh tài liệu Swagger/ReDoc.
- **Computer Vision / OMR**: [OpenCV (opencv-python-headless)](https://opencv.org/), [NumPy](https://numpy.org/), [Pillow](https://python-pillow.org/).
- **Database & ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/) (Hỗ trợ cả PostgreSQL & SQLite).
- **Authentication**: JWT Token với [python-jose](https://github.com/mpdavis/python-jose) và [passlib / bcrypt](https://passlib.readthedocs.io/).
- **Storage**: [Supabase Storage](https://supabase.com/) / Local Disk lưu trữ hình ảnh phiếu và câu hỏi.
- **Báo cáo & Thống kê**: [openpyxl](https://openpyxl.readthedocs.io/), [pandas](https://pandas.pydata.org/).
- **Testing**: [pytest](https://pytest.org/), [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio), `httpx`.

---

## ⚙️ Yêu cầu môi trường

- **Python**: `>= 3.10`
- **Git**
- *(Tùy chọn)* **PostgreSQL** nếu không sử dụng SQLite mặc định.

---

## 📦 Hướng dẫn cài đặt & Khởi chạy

### 1. Cấu hình Backend

Di chuyển vào thư mục backend và tạo môi trường ảo Python:

```bash
cd backend

# Tạo virtual environment
python3 -m venv venv

# Kích hoạt virtual environment
# Trên macOS / Linux:
source venv/bin/activate
# Trên Windows:
# venv\Scripts\activate

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

Sao chép file cấu hình môi trường:

```bash
cp .env.example .env
```

Chỉnh sửa tệp `.env` phù hợp với môi trường của bạn:
```env
APP_NAME="Hệ thống Chấm bài Trắc nghiệm"
DEBUG=True
DATABASE_URL=sqlite:///./cham_bai.db
# Hoặc PostgreSQL: postgresql://postgres:password@localhost:5432/cham_bai_db

SECRET_KEY=dev-secret-key-change-this-in-production-1234567890
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 2. Khởi tạo Cơ sở dữ liệu & Dữ liệu mẫu

Hệ thống cung cấp sẵn các script hỗ trợ tạo bảng và nạp dữ liệu demo hoàn chỉnh:

```bash
# Khởi tạo các bảng cơ sở dữ liệu
python scripts/init_db.py

# Nạp dữ liệu mẫu (Tài khoản Admin, Giáo viên, Đề thi Toán 10, Học sinh, 4 Mã đề)
python scripts/seed_demo_data.py
```

### 3. Khởi chạy Backend Server

#### Cách 1: Sử dụng script `dev.sh` (khuyến nghị cho Linux/macOS)
```bash
chmod +x dev.sh
./dev.sh
```

#### Cách 2: Khởi chạy trực tiếp bằng Uvicorn
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Truy cập kiểm tra hệ thống:
- **Trang chủ**: [http://localhost:8000/](http://localhost:8000/)
- **Kiểm tra trạng thái**: [http://localhost:8000/health](http://localhost:8000/health)
- **Tài liệu API tương tác (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Tài liệu API (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### 4. Kiểm thử (Testing)

Chạy bộ kiểm thử tự động với `pytest`:

```bash
pytest
```

---

## 🔑 Tài khoản demo sẵn có

Sau khi chạy lệnh `seed_demo_data.py`, bạn có thể đăng nhập thử nghiệm bằng các tài khoản sau:

| Vai trò | Tên đăng nhập | Mật khẩu | Trạng thái | Quyền hạn |
| :--- | :--- | :--- | :--- | :--- |
| **Quản trị viên** | `admin` | `admin123` | Đã kích hoạt | Toàn quyền quản trị tài khoản, duyệt câu hỏi, xem nhật ký |
| **Giáo viên** | `giaovien1` | `123456` | Đã kích hoạt | Tạo đề thi, tráo đề, chấm bài OMR, xem phổ điểm |

---

## 🔌 Danh sách API Endpoints chính

Mọi request API ngoại trừ đăng nhập/đăng ký cần đính kèm Header:
`Authorization: Bearer <access_token>`

### 1. Xác thực & Tài khoản (`/api/v1/auth`)
- `POST /api/v1/auth/register`: Đăng ký tài khoản Giáo viên (chờ duyệt).
- `POST /api/v1/auth/login`: Đăng nhập, nhận JWT Token (24h).
- `GET  /api/v1/auth/me`: Thông tin người dùng hiện tại.

### 2. Quản trị hệ thống (`/api/v1/admin`)
- `GET  /api/v1/admin/tai-khoan`: Danh sách tài khoản (lọc theo trạng thái `CHO_DUYET`, `DA_KICH_HOAT`, `BI_KHOA`).
- `POST /api/v1/admin/tai-khoan/{id}/phe-duyet`: Duyệt kích hoạt tài khoản.
- `POST /api/v1/admin/tai-khoan/{id}/khoa`: Khóa tài khoản.
- `GET  /api/v1/admin/nhat-ky`: Lịch sử vết hoạt động của hệ thống (Audit Log).

### 3. Đề thi & Tráo mã đề (`/api/v1/dethi`)
- `GET  /api/v1/dethi/`: Danh sách đề thi của giáo viên.
- `POST /api/v1/dethi/`: Tạo đề thi mới từ ma trận câu hỏi.
- `POST /api/v1/dethi/{ma_de_thi}/sinh-ma-de`: Sinh hàng loạt mã đề hoán vị ngẫu nhiên.
- `GET  /api/v1/dethi/{ma_de_thi}/ma-tran-dap-an`: Xem ma trận đáp án đúng các mã đề.

### 4. Chấm bài OMR & Kết quả (`/api/v1/chambai`)
- `POST /api/v1/chambai/tai-len`: Tải ảnh phiếu trả lời để chấm tự động bằng OpenCV OMR.
- `GET  /api/v1/chambai/phieu`: Lọc danh sách bài đã chấm theo lớp/đề thi.
- `GET  /api/v1/chambai/phieu/{ma_phieu}`: Xem chi tiết bài thi (ảnh nhận diện, số câu đúng/sai).
- `PUT  /api/v1/chambai/phieu/{ma_phieu}/sua-tay`: Chỉnh sửa câu trả lời, SBD hoặc mã đề.
- `POST /api/v1/chambai/phieu/{ma_phieu}/chot-luu`: Xác nhận lưu điểm chính thức.

### 5. Thống kê & Báo cáo (`/api/v1/thongke`)
- `GET  /api/v1/thongke/dethi/{ma_de_thi}/lop`: Thống kê phổ điểm, điểm trung bình theo lớp.
- `GET  /api/v1/thongke/dethi/{ma_de_thi}/cau-hoi`: Thống kê tỉ lệ đúng/sai theo từng câu hỏi.
- `GET  /api/v1/thongke/dethi/{ma_de_thi}/export/excel`: Xuất bảng điểm ra tệp Excel `.xlsx`.
- `GET  /api/v1/thongke/dethi/{ma_de_thi}/export/csv`: Xuất bảng điểm ra tệp `.csv`.

---

## 🔍 Quy trình xử lý ảnh OMR (Core Engine)

Thuật toán chấm bài bằng OpenCV được hiện thực trong [`backend/app/services/omr.py`](file:///Users/kenlee/workspace/Ứng%20dụng%20chấm%20bài%20/backend/app/services/omr.py) với các bước:

```text
Ảnh gốc (Camera/Thư viện)
       │
       ▼
1. Tiền xử lý: Chuyển ảnh xám (Grayscale) -> Làm mịn (Gaussian Blur) -> Ngưỡng nhị phân thích ứng (Adaptive Threshold)
       │
       ▼
2. Định vị góc: Tìm 4 điểm dấu mốc định vị góc phiếu (Fiducial Corners)
       │
       ▼
3. Nắn chỉnh phối cảnh: Căn phẳng góc chụp nghiêng về kích thước chuẩn (1000 x 1400 px) bằng cv2.warpPerspective
       │
       ▼
4. Phân tích vùng:
       ├─ Vùng Số báo danh (SBD): 6 cột số (0-9)
       ├─ Vùng Mã đề (MD): 3 cột số (0-9)
       └─ Vùng Đáp án: Khối lưới trắc nghiệm (20 / 50 câu; các lựa chọn A, B, C, D)
       │
       ▼
5. Tính tỉ lệ lấp đầy (Fill Density Ratio):
       ├─ Ngưỡng nhận diện tô: Pixel đen > 45% diện tích vòng tròn ô
       ├─ Phát hiện bất thường: Tô đè 2 ô, tẩy xóa không sạch, tô quá mờ
       └─ Tính toán Confidence Score (Độ tin cậy nhận diện)
       │
       ▼
6. Khớp ma trận đáp án đúng & Tính điểm
```

---

## 📚 Tài liệu tham khảo & Đặc tả

- [`01_Dac_ta_chuc_nang.docx`](file:///Users/kenlee/workspace/Ứng%20dụng%20chấm%20bài%20/01_Dac_ta_chuc_nang.docx): Đặc tả toàn bộ 20 use-case chi tiết giữa Giáo viên và Admin.
- [`02_Thiet_ke_CSDL.pdf`](file:///Users/kenlee/workspace/Ứng%20dụng%20chấm%20bài%20/02_Thiet_ke_CSDL.pdf): Bản vẽ thiết kế mô hình cơ sở dữ liệu quan hệ hoàn chỉnh.

---

## 📄 Bản quyền & Đóng góp

Dự án được xây dựng phục vụ công tác giảng dạy và kiểm tra đánh giá trong giáo dục. Mọi đóng góp (Pull Request, Báo lỗi Issue) đều được chào đón!

