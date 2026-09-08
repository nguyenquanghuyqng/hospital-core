# 🏥 Hospital Core — Hệ Thống Quản Lý Phòng Khám

Hệ thống quản lý phòng khám tích hợp: cấp số thứ tự, tiếp đón bệnh nhân, khám bệnh và hiển thị real-time qua WebSocket.

---

## Mục lục

- [Tổng quan kiến trúc](#tổng-quan-kiến-trúc)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Setup Backend](#setup-backend)
- [Setup Cơ sở dữ liệu](#setup-cơ-sở-dữ-liệu)
- [Chạy Backend](#chạy-backend)
- [Frontend Pages (Jinja2 / SPA)](#frontend-pages-jinja2--spa)
- [Frontpage (Landing Page tĩnh)](#frontpage-landing-page-tĩnh)
- [Các trang giao diện](#các-trang-giao-diện)
- [API Documentation](#api-documentation)
- [Biến môi trường](#biến-môi-trường)
- [Lưu ý Production](#lưu-ý-production)

---

## Tổng quan kiến trúc

```
hospital-core/
├── app/                    # Backend FastAPI
│   ├── api/v1/             # REST API endpoints
│   ├── core/               # Config, security, dependencies
│   ├── crud/               # Database operations
│   ├── db/                 # SQLAlchemy session & base
│   ├── models/             # ORM models (SQLAlchemy)
│   ├── schemas/            # Pydantic request/response schemas
│   ├── services/           # Business logic
│   ├── static/             # CSS, JS phục vụ qua /static
│   ├── templates/          # Jinja2 HTML templates (các trang nội bộ)
│   └── main.py             # Entry point FastAPI app
├── alembic/                # Database migrations
├── frontend/               # Landing page tĩnh (Phòng Khám Thiện Nhân)
│   ├── index.html
│   └── assets/
│       ├── css/style.css
│       └── js/main.js
├── .env                    # Biến môi trường (không commit)
├── .env.example            # Mẫu biến môi trường
├── requirements.txt        # Python dependencies
└── alembic.ini             # Cấu hình Alembic
```

**Stack:**
- **Backend:** Python 3.11 · FastAPI · SQLAlchemy (async) · Alembic · PostgreSQL
- **Auth:** JWT (python-jose) · bcrypt
- **Real-time:** WebSocket (websockets)
- **Templates:** Jinja2 · aiofiles
- **Frontend nội bộ:** HTML/CSS/JS thuần (phục vụ qua FastAPI)
- **Landing page:** HTML tĩnh (mở trực tiếp trên trình duyệt)

---

## Yêu cầu hệ thống

| Công cụ | Phiên bản tối thiểu |
|---|---|
| Python | 3.11+ |
| PostgreSQL | 14+ |
| pip | 23+ |

> **macOS:** Cài PostgreSQL qua [Homebrew](https://brew.sh): `brew install postgresql@16`  
> **Linux:** `sudo apt install postgresql postgresql-contrib`  
> **Windows:** Tải installer tại [postgresql.org](https://www.postgresql.org/download/windows/)

---

## Cấu trúc thư mục

Xem sơ đồ ở phần [Tổng quan kiến trúc](#tổng-quan-kiến-trúc).

---

## Setup Backend

### 1. Clone repo

```bash
git clone <repo-url>
cd hospital-core
```

### 2. Tạo virtual environment

```bash
python3.11 -m venv venv
```

Kích hoạt:

```bash
# macOS / Linux
source venv/bin/activate

# Windows (Command Prompt)
venv\Scripts\activate.bat

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

### 3. Cài dependencies

```bash
pip install -r requirements.txt
```

### 4. Tạo file `.env`

```bash
cp .env.example .env
```

Mở `.env` và điền thông tin thực tế:

```env
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/hospital_db
DATABASE_SYNC_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/hospital_db
SECRET_KEY=your-very-secret-key-change-this
DEBUG=True
APP_NAME=Hospital Queue Management System
APP_VERSION=1.0.0
```

> `DATABASE_URL` dùng driver `asyncpg` cho FastAPI runtime.  
> `DATABASE_SYNC_URL` dùng driver `psycopg2` cho Alembic migration.  
> `SECRET_KEY` dùng để ký JWT — **bắt buộc thay đổi trước khi lên production**.

---

## Setup Cơ sở dữ liệu

### 1. Tạo database PostgreSQL

Đăng nhập vào PostgreSQL:

```bash
psql -U postgres
```

Tạo database:

```sql
CREATE DATABASE hospital_db;
\q
```

### 2. Chạy migrations

Đảm bảo virtual environment đang kích hoạt, sau đó chạy toàn bộ migrations:

```bash
alembic upgrade head
```

Lệnh này sẽ lần lượt áp dụng các migration:

| File | Nội dung |
|---|---|
| `0001_initial_schema.py` | Tạo bảng `patients`, `queue_tickets`, `receptions` |
| `0002_extend_patient_reception.py` | Mở rộng thông tin bệnh nhân và tiếp đón |
| `0003_add_visit_status_and_auth.py` | Thêm trạng thái lượt khám và bảng `users` |
| `0004_add_examination_tables.py` | Thêm bảng khám bệnh |

Kiểm tra trạng thái migration hiện tại:

```bash
alembic current
```

Xem lịch sử migration:

```bash
alembic history --verbose
```

Rollback về migration trước (nếu cần):

```bash
alembic downgrade -1
```

---

## Chạy Backend

### Development

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- `--reload`: Tự động restart khi có thay đổi code (chỉ dùng trong dev).
- `--host 0.0.0.0`: Cho phép truy cập từ các thiết bị trong cùng mạng LAN.
- `--port 8000`: Port mặc định (có thể thay đổi).

### Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

- `--workers 4`: Chạy 4 worker process (khuyến nghị `2 × CPU cores + 1`).
- Không dùng `--reload` trong production.

Sau khi khởi động, backend phục vụ tại:

| URL | Mô tả |
|---|---|
| `http://localhost:8000` | Trang chủ (chọn vai trò) |
| `http://localhost:8000/display` | Màn hình LED số thứ tự |
| `http://localhost:8000/kiosk` | Kiosk lấy số |
| `http://localhost:8000/reception` | Quầy tiếp đón |
| `http://localhost:8000/docs` | Swagger UI (API docs) |
| `http://localhost:8000/redoc` | ReDoc (API docs) |
| `http://localhost:8000/health` | Health check endpoint |

---

## Frontend Pages (Jinja2 / SPA)

Các trang nội bộ (dành cho nhân viên y tế và bệnh nhân) được phục vụ **bởi FastAPI** qua Jinja2 templates, không cần build tool riêng.

Thư mục:
- **Templates HTML:** `app/templates/` — các file `.html` được render server-side
- **Static assets:** `app/static/css/` và `app/static/js/` — phục vụ tại `/static/`

Sau khi backend đang chạy, truy cập trực tiếp qua trình duyệt:

```
http://localhost:8000/           # Trang chủ chọn vai trò
http://localhost:8000/kiosk      # Kiosk bệnh nhân lấy số
http://localhost:8000/display    # Màn hình LED số thứ tự
http://localhost:8000/reception  # Quầy tiếp đón
```

> Không cần `npm install`, không cần build — các trang này chạy thuần HTML/CSS/JS, FastAPI phục vụ file tĩnh và render template trực tiếp.

---

## Frontpage (Landing Page tĩnh)

Thư mục `frontend/` chứa landing page **Phòng Khám Thiện Nhân** — trang giới thiệu dành cho bệnh nhân bên ngoài, hoàn toàn độc lập với backend.

### Mở nhanh trên trình duyệt

Chỉ cần mở file HTML trực tiếp:

```bash
# macOS
open frontend/index.html

# Linux
xdg-open frontend/index.html

# Windows
start frontend/index.html
```

Hoặc kéo file `frontend/index.html` vào cửa sổ trình duyệt.

### Phục vụ qua HTTP server cục bộ (khuyến nghị)

Mở bằng file:// có thể gặp lỗi CORS với một số font/asset. Dùng HTTP server đơn giản:

```bash
# Dùng Python (không cần cài thêm gì)
cd frontend
python3 -m http.server 3000
```

Truy cập tại: `http://localhost:3000`

```bash
# Hoặc dùng Node.js npx
cd frontend
npx serve .
```

> Landing page này **không kết nối** đến backend API — chỉ là trang giới thiệu phòng khám với thông tin, dịch vụ, đội ngũ bác sĩ và form liên hệ tĩnh.

---

## Các trang giao diện

### 1. Landing Page — `frontend/index.html`

Trang giới thiệu phòng khám dành cho bệnh nhân bên ngoài.

- Hero section với CTA đặt lịch
- Danh sách dịch vụ khám bệnh
- Giới thiệu đội ngũ bác sĩ
- Thống kê phòng khám
- Form đặt lịch / liên hệ
- Font: Be Vietnam Pro · Playfair Display

### 2. Trang chủ nội bộ — `GET /`

Màn hình chọn vai trò: điều hướng đến Kiosk, Màn hình LED, hoặc Quầy tiếp đón.

### 3. Kiosk — `GET /kiosk`

Giao diện bệnh nhân tự lấy số thứ tự.
- Kết nối WebSocket room `"kiosk"` để theo dõi số đang được gọi real-time.

### 4. Màn hình LED — `GET /display`

Hiển thị số thứ tự đang được gọi trên màn hình lớn.
- Kết nối WebSocket room `"display"` để cập nhật tự động.

### 5. Quầy tiếp đón — `GET /reception`

Giao diện nhân viên y tế quản lý hàng đợi.
- Kết nối WebSocket room `"reception"`.
- Gọi số, check-in, cập nhật trạng thái bệnh nhân.

---

## API Documentation

Sau khi backend đang chạy, toàn bộ API được document tự động tại:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

Nhóm API chính:

| Prefix | Module | Mô tả |
|---|---|---|
| `/api/v1/auth` | `auth.py` | Đăng nhập, lấy JWT token |
| `/api/v1/queue` | `queue.py` | Cấp số, gọi số, WebSocket |
| `/api/v1/patients` | `patients.py` | CRUD bệnh nhân |
| `/api/v1/reception` | `reception.py` | Quản lý tiếp đón |
| `/api/v1/doctor` | `doctor.py` | Giao diện bác sĩ |
| `/api/v1/examination` | `examination.py` | Quản lý khám bệnh |

---

## Biến môi trường

| Biến | Mô tả | Mặc định |
|---|---|---|
| `DATABASE_URL` | Connection string async (asyncpg) | `postgresql+asyncpg://postgres:password@localhost:5432/hospital_db` |
| `DATABASE_SYNC_URL` | Connection string đồng bộ (psycopg2) | `postgresql+psycopg2://postgres:password@localhost:5432/hospital_db` |
| `SECRET_KEY` | Khoá bí mật ký JWT | `changeme-in-production` |
| `DEBUG` | Bật chế độ debug | `True` |
| `APP_NAME` | Tên ứng dụng | `Hospital Queue Management System` |
| `APP_VERSION` | Phiên bản ứng dụng | `1.0.0` |
| `JWT_ALGORITHM` | Thuật toán ký JWT | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Thời gian sống access token (phút) | `480` (8 giờ) |

---

## Lưu ý Production

- Đổi `SECRET_KEY` thành chuỗi ngẫu nhiên đủ dài:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- Đặt `DEBUG=False` để giảm log level và tắt SQL echo.
- Thay `allow_origins=["*"]` trong `main.py` bằng domain cụ thể.
- Chạy sau reverse proxy (nginx / caddy) để xử lý TLS.
- Không commit file `.env` vào git (đã có trong `.gitignore`).
