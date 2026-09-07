import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.api.v1.router import api_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# ── API routes ─────────────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Frontend page routes ───────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    """Trang chủ — chọn vai trò."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/display", response_class=HTMLResponse, include_in_schema=False)
async def display_page(request: Request):
    """Màn hình LED hiển thị số thứ tự."""
    return templates.TemplateResponse("display.html", {"request": request})


@app.get("/kiosk", response_class=HTMLResponse, include_in_schema=False)
async def kiosk_page(request: Request):
    """Kiosk / quầy lấy số thứ tự cho bệnh nhân."""
    return templates.TemplateResponse("kiosk.html", {"request": request})


@app.get("/reception", response_class=HTMLResponse, include_in_schema=False)
async def reception_page(request: Request):
    """Giao diện quầy tiếp đón dành cho nhân viên."""
    return templates.TemplateResponse("reception.html", {"request": request})


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
