# 🏥 Hospital Core — Hệ Thống Quản Lý Phòng Khám

Hệ thống quản lý phòng khám tích hợp: cấp số thứ tự, tiếp đón bệnh nhân, khám bệnh và hiển thị real-time qua WebSocket.

---

## Mục lục

- [Tổng quan kiến trúc](#tổng-quan-kiến-trúc)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Setup Backend](#setup-backend)
- [Setup Frontend React](#setup-frontend-react)
- [Tài khoản test](#tài-khoản-test)
- [Chạy hệ thống](#chạy-hệ-thống)
- [API Documentation](#api-documentation)
- [Biến môi trường](#biến-môi-trường)
- [Lưu ý Production](#lưu-ý-production)
- [Tài liệu nghiệp vụ](#tài-liệu-nghiệp-vụ)

---

## Tổng quan kiến trúc

```
GITHUB/
├── hospital-core/              # Backend FastAPI
│   ├── app/
│   │   ├── api/v1/endpoints/   # REST API endpoints
│   │   ├── core/               # Config, security, dependencies
│   │   ├── crud/               # Database operations
│   │   ├── db/                 # SQLAlchemy session & base
│   │   ├── models/             # ORM models (SQLAlchemy)
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic & WebSocket
│   │   ├── static/             # Static assets (legacy Jinja2)
│   │   └── main.py             # Entry point FastAPI app
│   ├── alembic/                # Database migrations
│   ├── frontend/               # Landing page tĩnh (marketing)
│   ├── .env                    # Biến môi trường (không commit)
│   ├── .env.example
│   └── requirements.txt
│
└── hospital-frontend/          # Frontend React + TypeScript
    ├── src/
    │   ├── api/                # API client tách riêng theo domain
    │   ├── app/                # Router + AppShell + ROUTES
    │   ├── components/ui/      # Design system dùng chung
    │   ├── features/           # Feature modules độc lập
    │   │   ├── auth/           # Login, RBAC, ProtectedRoute
    │   │   ├── reception/      # Tiếp đón bệnh nhân
    │   │   ├── queue/          # Kiosk, Display, Quản lý hàng chờ
    │   │   ├── doctor/         # Hàng đợi bác sĩ
    │   │   └── examination/    # Phiếu khám bệnh
    │   ├── hooks/              # Shared hooks (useAsync, useWebSocket...)
    │   ├── store/              # Zustand state management
    │   └── types/              # TypeScript types mirror Python schemas
    ├── .env.example
    └── package.json
```

**Stack Backend:** Python 3.11 · FastAPI · SQLAlchemy async · Alembic · PostgreSQL · JWT · WebSocket

**Stack Frontend:** React 18 · TypeScript strict · Vite · Zustand · react-hook-form + zod · react-hot-toast

---

## Yêu cầu hệ thống

| Công cụ | Phiên bản tối thiểu |
|---|---|
| Python | 3.11+ |
| PostgreSQL | 14+ |
| Node.js | 18+ |
| npm | 9+ |

---

## Setup Backend

### 1. Tạo virtual environment & cài dependencies

```bash
cd hospital-core
python3.11 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate.bat     # Windows
pip install -r requirements.txt
```

### 2. Cấu hình environment

```bash
cp .env.example .env
# Chỉnh sửa .env với thông tin database thực tế
```

### 3. Tạo database & chạy migrations

```bash
# Tạo database
psql -U postgres -c "CREATE DATABASE hospital_db;"

# Chạy migrations
alembic upgrade head
```

### 4. Tạo tài khoản test (lần đầu)

Sau khi backend đang chạy, tạo tài khoản qua API:

```bash
# Admin
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123","full_name":"Quản trị viên","role":"admin"}'

# Bác sĩ
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"doctor","password":"Doctor@123","full_name":"BS. Test Bác Sĩ","role":"doctor","clinic_room":"Phòng 1"}'

# Điều dưỡng
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"nurse","password":"Nurse@123","full_name":"ĐD. Test Điều Dưỡng","role":"nurse"}'
```

---

## Setup Frontend React

```bash
cd ../hospital-frontend    # từ hospital-core/
npm install
```

---

## Tài khoản test

> Áp dụng cho môi trường **development**. Thay đổi trước khi lên production.

| Username | Password | Role | Quyền truy cập |
|----------|----------|------|----------------|
| `admin` | `Admin@123` | admin | Tất cả chức năng |
| `doctor` | `Doctor@123` | doctor | Phòng khám bác sĩ + Phiếu khám |
| `nurse` | `Nurse@123` | nurse | Tiếp đón + Quản lý hàng chờ |
| `bsphong1` | *(xem DB)* | doctor | Phòng 1 |
| `bsphong2` | *(xem DB)* | doctor | Phòng 2 |

### Phân quyền chi tiết (RBAC)

| Chức năng | admin | doctor | nurse |
|-----------|:-----:|:------:|:-----:|
| Tiếp đón bệnh nhân | ✅ | — | ✅ |
| Quản lý hàng chờ | ✅ | — | ✅ |
| Kiosk / Màn hình LED | ✅ | ✅ | ✅ |
| Hàng đợi bác sĩ | ✅ | ✅ | — |
| Phiếu khám bệnh | ✅ | ✅ | — |

---

## Chạy hệ thống

### Chạy tất cả cùng lúc (mở 3 terminal riêng)
admin	Admin@123	Tất cả chức năng
doctor	Doctor@123	Phòng khám + Phiếu khám
nurse	Nurse@123	Tiếp đón + Hàng chờ

**Terminal 1 — Backend FastAPI:**
```bash
cd hospital-core
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend React (dev):**
```bash
cd ../hospital-frontend    # cùng cấp với hospital-core
npm run dev
```

**Terminal 3 — Landing page (tuỳ chọn):**
```bash
cd hospital-core/frontend
python3 -m http.server 5500
```

### URLs

| URL | Mô tả | Ghi chú |
|-----|-------|---------|
| `http://localhost:5173` | **React App** — Hệ thống quản lý nội bộ | Cần đăng nhập |
| `http://localhost:5500` | Landing page Thiện Nhân | Không cần đăng nhập |
| `http://localhost:8000/docs` | Swagger UI API | Dev only |
| `http://localhost:8000/display` | Màn hình LED số thứ tự | Jinja2 (cũ) |
| `http://localhost:8000/kiosk` | Kiosk lấy số | Jinja2 (cũ) |

### Build production (output vào `app/static/dist/`)

```bash
cd hospital-frontend
npm run build
```

---

## API Documentation

Backend đang chạy, truy cập:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Health check:** `http://localhost:8000/health`

| Prefix | Mô tả |
|--------|-------|
| `POST /api/v1/auth/login` | Đăng nhập, nhận JWT |
| `GET  /api/v1/auth/me` | Thông tin tài khoản hiện tại |
| `GET  /api/v1/patients` | Danh sách bệnh nhân |
| `GET  /api/v1/receptions` | Danh sách tiếp đón |
| `GET  /api/v1/doctor/queue` | Hàng đợi khám theo phòng |
| `GET  /api/v1/examinations/{id}` | Chi tiết phiếu khám |
| `WS   /api/v1/queue/ws/{room}` | WebSocket real-time |

---

## Biến môi trường

| Biến | Mô tả | Mặc định |
|------|-------|----------|
| `DATABASE_URL` | Connection string async (asyncpg) | `postgresql+asyncpg://postgres:password@localhost:5432/hospital_db` |
| `DATABASE_SYNC_URL` | Connection string đồng bộ (psycopg2) | `postgresql+psycopg2://...` |
| `SECRET_KEY` | Khoá bí mật ký JWT | `changeme-in-production` |
| `DEBUG` | Bật chế độ debug | `True` |

---

## Lưu ý Production

```bash
# Tạo SECRET_KEY ngẫu nhiên
python3 -c "import secrets; print(secrets.token_hex(32))"
```

- Đặt `DEBUG=False`
- Thay `allow_origins=["*"]` bằng domain cụ thể
- Chạy sau reverse proxy (nginx / caddy) để xử lý TLS
- Không commit file `.env`

---

## Tài liệu nghiệp vụ

### B.3 Luồng nghiệp vụ chi tiết — Khám bệnh

#### Bước 1 — Bác sĩ chọn bệnh nhân từ hàng đợi

Danh sách chờ khám hiển thị theo phòng khám của bác sĩ đang đăng nhập, sắp xếp theo thứ tự số/thời gian đến. Trạng thái từng bệnh nhân:

| Trạng thái | Ý nghĩa |
|------------|---------|
| ⏳ Chờ khám | Mặc định — vừa được chuyển từ tiếp đón sang |
| 🔬 Đi làm CLS | Bệnh nhân đang đi làm xét nghiệm/CĐHA, chưa quay lại |
| 📋 Có kết quả | CLS đã trả kết quả, bệnh nhân sẵn sàng được gọi lại |
| 📅 Tái khám | Bệnh nhân quay lại theo lịch hẹn đã đặt trước |

Bác sĩ gọi bệnh nhân tiếp theo, hoặc chọn trực tiếp bất kỳ bệnh nhân nào trong danh sách (ví dụ ưu tiên ca "Có kết quả").

#### Bước 2 — Xem lại thông tin & bệnh sử

- Thông tin hành chính bệnh nhân
- Lịch sử các lần khám trước (ngày giờ, phòng khám, chẩn đoán/đơn thuốc từng lần)
- Giấy chuyển tuyến / giới thiệu (nếu có)

#### Bước 3 — Ghi nhận thăm khám & chẩn đoán

- Dấu hiệu sinh tồn (nhiệt độ, huyết áp, nhịp tim, nhịp thở, SpO₂, cân nặng, chiều cao — BMI tự tính)
- Triệu chứng lâm sàng (mô tả tự do)
- Chẩn đoán ICD-10 (1 chẩn đoán chính bắt buộc + nhiều chẩn đoán phụ)
- Biến chứng nếu có

#### Bước 4 — Chỉ định & kê đơn

Trong quá trình khám, bác sĩ có thể:

- **Chỉ định CLS** → vòng lặp: chẩn đoán sơ bộ → chỉ định CLS → có kết quả → chẩn đoán xác định
- **Kê đơn thuốc BHYT** (Phần C)
- **Kê đơn thuốc ngoài** (Phần C.2)
- **Chỉ định tạm ứng** (Phần F) — nếu chi phí dự kiến lớn

Chi phí real-time hiển thị ngay trên màn hình (tách CLS / Thuốc, BHYT chi trả / BN chi trả).

#### Bước 5 — Quyết định hướng xử trí

> Chỉ được chọn **1** hướng, các hướng loại trừ lẫn nhau.

| Hướng xử trí | Ý nghĩa |
|-------------|---------|
| Điều trị ngoại trú, cho về | Kết thúc lượt khám, bệnh nhân về nhà |
| Hẹn tái khám | Kích hoạt luồng Hẹn khám (Phần H) |
| Chuyển phòng khám | Đẩy sang hàng đợi phòng khám khác |
| Chuyển phòng lưu / cấp cứu | Chuyển sang khu lưu bệnh/cấp cứu |
| Nhập viện | Kích hoạt luồng nhập viện — chọn khoa/phòng |
| Chuyển tuyến / chuyển viện | Ghi rõ nơi chuyển đến; chuẩn bị giấy chuyển tuyến BHYT |
| Bỏ về (không hoàn tất khám) | Bệnh nhân tự ý bỏ về — ghi nhận, không tính hoàn tất |
| Cấp toa bệnh mãn tính | Thời hạn đơn dài hơn thông thường |
| Tử vong | Quy trình đặc biệt — đóng hồ sơ, viện phí riêng |

Nếu chọn **Hẹn tái khám**: nhập thêm kết quả điều trị hiện tại (không thay đổi / đỡ / khỏi...).

#### Bước 6 — Hoàn tất phiếu khám

**Điều kiện bắt buộc trước khi hoàn tất:**
1. ✅ Không còn chỉ định CLS nào đang ở trạng thái "chưa có kết quả"
2. ✅ Đã có ít nhất 1 chẩn đoán chính (không để trống)
3. ✅ Đối chiếu tạm ứng đã thu vs chi phí thực tế (nếu có tạm ứng)
4. ✅ Bác sĩ ký số phiếu khám

Sau khi ký số, phiếu bị khoá. Mọi chỉnh sửa sau đó phải qua nghiệp vụ "trình ký lại".

---

### B.4 Ràng buộc & quy tắc quan trọng

- Một bệnh nhân **luôn có 1 chẩn đoán chính** — không được để trống khi hoàn tất
- **Không cho hoàn tất** khi còn chỉ định CLS chưa có kết quả
- Hướng xử trí "Nhập viện" / "Chuyển tuyến" phải kèm đủ thông tin bắt buộc

---

### Phần C — Đơn thuốc (BHYT & ngoài)

#### C.1 Phân loại đơn thuốc

| Loại | BHYT chi trả | Trừ tồn kho | Tính viện phí |
|------|:---:|:---:|:---:|
| Thuốc BHYT | ✅ Có (theo tỷ lệ) | ✅ | ✅ |
| Thu phí nội bộ | ❌ | ✅ | ✅ (100% BN) |
| Mua ngoài (giấy kê) | ❌ | ❌ | ❌ |

#### C.2 Luồng BHYT

- Chỉ chọn thuốc trong danh mục BHYT **đã trúng thầu** tại cơ sở
- Hệ thống tự tính: tỷ lệ chi trả theo đối tượng chính sách + trái/đúng tuyến
- Kiểm tra: tương tác thuốc · trùng hoạt chất · chống chỉ định dị ứng · tồn kho · trần thanh toán BHYT
- Sau xác nhận → chờ Dược xác nhận giữ chỗ tồn kho

#### C.3 Luồng ngoài BHYT

- Thu phí nội bộ: kiểm tra tồn kho + an toàn thuốc (không kiểm tra danh mục BHYT)
- Mua ngoài: nhập tên tự do, không trừ kho, chỉ in giấy cho BN, không vào viện phí

---

### Phần D — Chỉ định cận lâm sàng (CLS)

- Chọn từ danh mục kỹ thuật → hệ thống biết phòng thực hiện tương ứng
- Xác định loại chi trả: BHYT · thu phí · theo yêu cầu · khám sức khoẻ · miễn phí · trẻ dưới 6 · tiêm chủng · trả sau
- Đánh dấu ưu tiên: thường quy / ưu tiên / cấp cứu
- Ghi chú lâm sàng gửi kèm cho phòng thực hiện
- Kiểm tra trùng chỉ định trong ngày → cảnh báo (vẫn cho phép nếu bác sĩ xác nhận)
- **Ràng buộc trung tâm:** Không thể hoàn tất khám khi còn CLS chưa có kết quả

---

### Phần E — Dấu hiệu sinh tồn

| Chỉ số | Ghi chú |
|--------|---------|
| Nhiệt độ (°C) | Ngưỡng hợp lệ vật lý bắt buộc |
| Huyết áp (mmHg) | |
| Nhịp tim (lần/phút) | Ngưỡng theo độ tuổi |
| Nhịp thở (lần/phút) | |
| SpO₂ (%) | |
| Cân nặng (kg) | |
| Chiều cao (cm) | |
| BMI | **Tự tính** — không cho nhập tay |

- Cảnh báo ngay nếu chỉ số nằm ngoài ngưỡng bình thường (theo độ tuổi BN)
- Hiển thị xu hướng thay đổi qua thời gian (với nội trú đo nhiều lần)
- Với nội trú: nhắc điều dưỡng nếu quá giờ cấu hình mà chưa có lượt đo mới

---

### Phần F — Chỉ định tạm ứng

**Luồng:**
1. Bác sĩ tạo yêu cầu tạm ứng (ghi lý do + số tiền đề xuất)
2. Thu ngân xác nhận + thu tiền thực tế (có thể khác đề xuất)
3. Đối chiếu tổng tạm ứng vs chi phí thực khi kết toán:
   - Dư → hoàn lại BN
   - Thiếu → thu thêm trước khi cho về
4. Nếu lượt khám bị huỷ → quy trình hoàn tiền riêng

---

### Phần G — Xem kết quả CLS

- Khi có kết quả → bệnh nhân trong hàng đợi bác sĩ đổi trạng thái thành "📋 Có kết quả"
- Hiển thị bảng chỉ số + đơn vị + khoảng tham chiếu; **đánh dấu nổi bật** nếu ngoài tham chiếu
- So sánh với lần khám trước cùng loại xét nghiệm (xu hướng thay đổi)
- Bác sĩ phải **chủ động đánh dấu đã xem** (chỉ hợp lệ sau khi mở xem chi tiết)
- Kết quả nguy hiểm nghiêm trọng → cảnh báo chủ động, không chỉ màu đỏ thụ động

---

### Phần H — Hẹn khám

- Tạo ngay khi bác sĩ chọn hướng "Hẹn tái khám" ở Bước 5
- Gợi ý phòng khám/bác sĩ giống lần hiện tại
- Gửi nhắc lịch tự động trước ngày hẹn (theo cấu hình)
- Khi BN quay lại: tiếp đón tự nhận diện lịch hẹn và hiển thị ngay
- Quá hẹn không đến → tự động đánh dấu "bỏ lỡ" → bộ phận CSKH có thể liên hệ lại
- 1 BN có thể có nhiều lịch hẹn đồng thời (nhiều chuyên khoa khác nhau)

---

### Phần I — Giấy nghỉ hưởng BHXH

**Yêu cầu bắt buộc:**
- Đã có chẩn đoán rõ ràng (mã bệnh là trường bắt buộc trên giấy)
- Mỗi giấy gắn số seri phôi duy nhất (không tái sử dụng dù đã huỷ)
- Số ngày nghỉ ≤ giới hạn tối đa theo loại bệnh; vượt mức → cần xác nhận lý do đặc biệt
- Bác sĩ ký số
- Gửi liên thông điện tử lên cổng BHXH → mới tính là "đã cấp" hợp lệ
- Nếu gửi thất bại: cho thử lại, **không tạo giấy trùng lặp**

---

### Phần J — Mối liên kết giữa các chức năng

```
Tiếp đón (A)
    │  Đối tượng chính sách + thông tuyến
    ▼
Khám bệnh (B) ←──────────────────────────────────┐
    │                                              │
    ├─→ Đơn thuốc BHYT (C.2)    ← tỷ lệ từ (A)   │
    ├─→ Đơn thuốc ngoài (C.3)                     │
    ├─→ Chỉ định CLS (D) ───→ Kết quả CLS (G) ────┘
    ├─→ Dấu hiệu sinh tồn (E)                     (vòng lặp khám)
    ├─→ Tạm ứng (F) ───→ Đối chiếu khi hoàn tất
    ├─→ Hẹn tái khám (H) ───→ Tiếp đón lần sau (A)
    └─→ Giấy BHXH (I)

Ràng buộc trung tâm (không thể bỏ qua):
    ✗ Hoàn tất khám khi còn CLS chưa có kết quả
    ✗ Hoàn tất khám khi chưa có chẩn đoán chính
    ✗ Hoàn tất khám khi chưa đối chiếu tạm ứng
```

---

*Phần mềm thiết kế bởi **Nguyễn Quang Huy***
