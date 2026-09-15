"""
Entry point của ứng dụng FastAPI — Hospital Queue Management System.

Khởi tạo FastAPI app với:
- CORS middleware (wildcard trong development, cần thu hẹp khi lên production).
- Request logging middleware: ghi log mọi request với method, path, status, latency.
- Global exception handler: trả JSON chuẩn cho mọi lỗi không được xử lý.
- Static files tại ``/static`` (CSS, JS, assets frontend).
- Jinja2 templates cho các trang HTML frontend (SPA đơn giản).
- API router v1 tại ``/api/v1``.
- Các route HTML cho frontend: ``/``, ``/display``, ``/kiosk``, ``/reception``.
- Health check tại ``/health``.
"""
import logging
import os
import time
import traceback
import asyncio
from contextlib import suppress
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import get_db
from app.services.national_prescription_service import run_retry_task

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Quản lý vòng đời (lifespan) của FastAPI application.

    Chạy logic startup khi app khởi động và logic shutdown khi app dừng.
    Sử dụng ``asynccontextmanager`` theo chuẩn FastAPI thay thế cho
    các event handler ``on_startup`` / ``on_shutdown`` cũ.

    Args:
        app: Instance FastAPI đang chạy.

    Yields:
        Điểm giữa ``yield`` là thời gian app đang phục vụ request.
    """
    if not settings.DEBUG:
        insecure = []
        if settings.SECRET_KEY == "changeme-in-production":
            insecure.append("SECRET_KEY")
        if "password" in settings.DATABASE_URL and "localhost" in settings.DATABASE_URL:
            insecure.append("DATABASE_URL")
        if not settings.CORS_ORIGINS.strip():
            insecure.append("CORS_ORIGINS")
        if insecure:
            raise RuntimeError(
                "Thiếu cấu hình production bắt buộc: " + ", ".join(insecure)
            )

    logger.info(f"🏥  {settings.APP_NAME} v{settings.APP_VERSION} starting…")
    retry_task = asyncio.create_task(run_retry_task(get_db))
    yield
    retry_task.cancel()
    with suppress(asyncio.CancelledError):
        await retry_task
    logger.info("🏥  Application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Hệ thống quản lý phòng khám và chăm sóc sức khoẻ:\n"
        "- **Cấp số thứ tự** và hiển thị real-time qua WebSocket\n"
        "- **Quản lý tiếp đón** bệnh nhân (quét CCCD, đăng ký khám)\n"
        "- **Khám bệnh, lâm sàng, thuốc và viện phí**\n"
        "- **Quản trị danh mục, kho thuốc, số liệu và xuất báo cáo**\n"
        "- **Swagger/OpenAPI đầy đủ cho toàn bộ API v1**\n"
    ),
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "tagsSorter": "alpha",
        "operationsSorter": "alpha",
    },
    lifespan=lifespan,
)

app.openapi_tags = [
    {
        "name": "Auth - Xác thực",
        "description": "Đăng nhập, xác thực JWT, thông tin người dùng và bootstrap tài khoản hệ thống.",
    },
    {
        "name": "Queue - Hệ thống số thứ tự",
        "description": "Cấp số, theo dõi lượt khám, gọi bệnh nhân và hiển thị trạng thái chờ thực tế.",
    },
    {
        "name": "Patients - Bệnh nhân",
        "description": "Quản lý hồ sơ bệnh nhân, tìm kiếm, cập nhật thông tin cá nhân và lịch sử khám.",
    },
    {
        "name": "Reception - Tiếp đón",
        "description": "Tiếp nhận bệnh nhân, check-in, xác định thông tin và chuyển sang quy trình khám.",
    },
    {
        "name": "Doctor - Phòng khám bác sĩ",
        "description": "Khu vực làm việc của bác sĩ: danh sách bệnh nhân, thông tin khám, vai trò chuyên môn.",
    },
    {
        "name": "Examination - Phiếu khám",
        "description": "Tạo, đọc, cập nhật và xóa phiếu khám lâm sàng, trình trạng bệnh nhân và kết luận.",
    },
    {
        "name": "Clinical - Kết quả CLS & Thuốc",
        "description": "Kết quả cận lâm sàng, thuốc, theo dõi điều trị và dữ liệu lâm sàng hỗ trợ chẩn đoán.",
    },
    {
        "name": "Catalog - Danh mục",
        "description": "Quản lý thuốc, dịch vụ CLS, nhóm thuốc và dữ liệu danh mục nền tảng của hệ thống.",
    },
    {
        "name": "Billing - Viện phí & Thanh toán",
        "description": "Tạo hóa đơn, thanh toán, theo dõi viện phí và chi phí điều trị bệnh nhân.",
    },
    {
        "name": "Appointments - Lịch hẹn",
        "description": "Quản lý lịch hẹn khám, xác nhận bệnh nhân đến, hoàn tất hoặc hủy lịch hẹn.",
    },
    {
        "name": "Export - Xuất dữ liệu",
        "description": "Xuất báo cáo, dữ liệu thống kê, tệp tin và kết quả dạng báo cáo cho hệ thống bên ngoài.",
    },
    {
        "name": "Admin - Quản trị",
        "description": "Cấu hình hệ thống, quản lý tài khoản, phân quyền và các chức năng quản trị nội bộ.",
    },
    {
        "name": "Prescription - Đơn thuốc điện tử BYT",
        "description": "Quản lý đơn thuốc, gửi dữ liệu BYT, ghi nhận thuốc kê cho bệnh nhân và chẩn đoán liên quan.",
    },
    {
        "name": "Inventory - Kho thuốc",
        "description": "Nhập kho, điều chỉnh tồn kho, xuất thuốc cho bệnh nhân và theo dõi giao dịch kho.",
    },
    {
        "name": "BHYT - Eligibility and Claims",
        "description": "Xác thực thẻ BHYT, gửi yêu cầu thanh toán, đối soát và xử lý hồ sơ bảo hiểm y tế.",
    },
]

# ── CORS ──────────────────────────────────────────────────────────────────────
configured_origins = [
    origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()
]
if settings.DEBUG and not configured_origins:
    configured_origins = ["*"]
if "*" in configured_origins and not settings.DEBUG:
    raise RuntimeError("CORS_ORIGINS production không được chứa wildcard '*'")

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_credentials="*" not in configured_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Logging Middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware ghi log mọi HTTP request với method, path, status code và latency.

    Giúp quan sát hoạt động hệ thống (observability) và debug trong production.
    Các path ``/health``, ``/static``, ``/docs``, ``/redoc``, ``/openapi.json``
    được bỏ qua để không làm nhiễu log.

    Args:
        request: FastAPI Request object.
        call_next: Callable chuyển request xuống handler tiếp theo.

    Returns:
        Response từ handler được bọc thêm thời gian xử lý trong header.
    """
    skip_paths = {"/health", "/docs", "/redoc", "/openapi.json"}
    if request.url.path in skip_paths or request.url.path.startswith("/static"):
        return await call_next(request)

    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "%-6s %-40s %d  %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )
    response.headers["X-Process-Time-Ms"] = f"{latency_ms:.1f}"
    return response


# ── Global Exception Handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Bắt tất cả exception không được xử lý, trả JSON chuẩn và log traceback.

    Ngăn FastAPI trả HTML 500 mặc định, đảm bảo client luôn nhận JSON
    dù xảy ra lỗi bất ngờ. Traceback đầy đủ được ghi vào log ở mức ERROR.

    Args:
        request: FastAPI Request object.
        exc: Exception không được xử lý.

    Returns:
        JSONResponse với status 500 và thông báo lỗi.
    """
    tb = traceback.format_exc()
    logger.error(
        "Unhandled exception | %s %s\n%s",
        request.method,
        request.url.path,
        tb,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Lỗi hệ thống nội bộ. Vui lòng thử lại hoặc liên hệ quản trị viên.",
            "path": str(request.url.path),
        },
    )


# ── Static files & Templates ──────────────────────────────────────────────────
static_dir    = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# ── API routes ────────────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Frontend page routes ──────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    """
    Trang chủ — màn hình chọn vai trò (bác sĩ / tiếp đón / kiosk / màn hình LED).

    Args:
        request: FastAPI Request object (cần thiết cho Jinja2 context).

    Returns:
        HTML response từ template ``index.html``.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/display", response_class=HTMLResponse, include_in_schema=False)
async def display_page(request: Request):
    """
    Màn hình LED hiển thị số thứ tự đang được gọi (public display).

    Trang này kết nối WebSocket vào room ``"display"`` để nhận
    cập nhật real-time khi có số mới được gọi.

    Args:
        request: FastAPI Request object.

    Returns:
        HTML response từ template ``display.html``.
    """
    return templates.TemplateResponse("display.html", {"request": request})


@app.get("/kiosk", response_class=HTMLResponse, include_in_schema=False)
async def kiosk_page(request: Request):
    """
    Giao diện kiosk / quầy lấy số thứ tự dành cho bệnh nhân.

    Trang này cho phép bệnh nhân tự lấy số thứ tự và theo dõi
    số đang được gọi qua WebSocket room ``"kiosk"``.

    Args:
        request: FastAPI Request object.

    Returns:
        HTML response từ template ``kiosk.html``.
    """
    return templates.TemplateResponse("kiosk.html", {"request": request})


@app.get("/reception", response_class=HTMLResponse, include_in_schema=False)
async def reception_page(request: Request):
    """
    Giao diện quầy tiếp đón dành cho nhân viên y tế.

    Trang này kết nối WebSocket vào room ``"reception"`` để nhận
    cập nhật real-time khi có số mới, check-in, hoặc thay đổi trạng thái.

    Args:
        request: FastAPI Request object.

    Returns:
        HTML response từ template ``reception.html``.
    """
    return templates.TemplateResponse("reception.html", {"request": request})


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint — kiểm tra ứng dụng đang chạy bình thường.

    Dùng cho load balancer, container orchestration (Docker / Kubernetes),
    hoặc monitoring tool để xác nhận service còn sống.

    Returns:
        Dict ``{"status": "ok", "app": <APP_NAME>, "version": <APP_VERSION>}``.
    """
    return {
        "status":  "ok",
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
