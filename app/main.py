"""
Entry point của ứng dụng FastAPI — Hospital Queue Management System.

Khởi tạo FastAPI app với:
- CORS middleware (wildcard trong development, cần thu hẹp khi lên production).
- Static files tại ``/static`` (CSS, JS, assets frontend).
- Jinja2 templates cho các trang HTML frontend (SPA đơn giản).
- API router v1 tại ``/api/v1``.
- Các route HTML cho frontend: ``/``, ``/display``, ``/kiosk``, ``/reception``.
- Health check tại ``/health``.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.api.v1.router import api_router

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
    logger.info(f"🏥  {settings.APP_NAME} v{settings.APP_VERSION} starting…")
    yield
    logger.info("🏥  Application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Hệ thống quản lý phòng khám:\n"
        "- **Cấp số thứ tự** và hiển thị real-time qua WebSocket\n"
        "- **Quản lý tiếp đón** bệnh nhân (quét CCCD, đăng ký khám)\n"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Thay bằng domain cụ thể khi lên production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
