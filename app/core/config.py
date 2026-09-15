"""
Cấu hình ứng dụng — đọc từ file .env hoặc biến môi trường.

Sử dụng pydantic-settings để tự động parse và validate giá trị cấu hình.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Lớp cấu hình trung tâm của ứng dụng.

    Các giá trị được đọc từ file .env (hoặc biến môi trường).
    Tất cả thuộc tính có giá trị mặc định, phù hợp môi trường development.

    Attributes:
        APP_NAME: Tên hiển thị của ứng dụng.
        APP_VERSION: Phiên bản ứng dụng.
        DEBUG: Bật/tắt chế độ debug (ảnh hưởng log level và SQL echo).
        DATABASE_URL: Connection string async (asyncpg) — dùng cho FastAPI.
        DATABASE_SYNC_URL: Connection string đồng bộ (psycopg2) — dùng cho Alembic migration.
        SECRET_KEY: Khoá bí mật ký JWT. Phải thay đổi trong production.
        JWT_ALGORITHM: Thuật toán ký JWT (mặc định HS256).
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES: Thời gian sống của access token (phút).
    """

    APP_NAME: str = "Hospital Queue Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    CORS_ORIGINS: str = ""
    """Comma-separated browser origins allowed outside development."""

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/hospital_db"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://postgres:password@localhost:5432/hospital_db"

    SECRET_KEY: str = "changeme-in-production"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 giờ

    # ── Liên thông quốc gia (donthuocquocgia.vn) ─────────────────────────────
    NATIONAL_FACILITY_CODE: str = ""
    """Mã cơ sở 5 ký tự do Sở Y tế cấp — bắt buộc trước khi kê đơn BYT."""

    NATIONAL_RX_API_URL: str = ""
    """Base URL API hệ thống quốc gia (để trống = chế độ dry-run, không gửi thật)."""

    NATIONAL_RX_API_KEY: str = ""
    """API key do Sở Y tế cấp."""

    NATIONAL_RX_API_PATH: str = "/don-thuoc"
    NATIONAL_RX_API_VERSION: str = ""

    NATIONAL_RX_TIMEOUT: int = 15
    """Timeout (giây) khi gọi API BYT."""

    BHYT_API_URL: str = ""
    BHYT_API_KEY: str = ""
    BHYT_API_TIMEOUT: int = 20

    # Convenience lowercase aliases cho services
    @property
    def national_facility_code(self) -> str:
        return self.NATIONAL_FACILITY_CODE

    @property
    def national_rx_api_url(self) -> str:
        return self.NATIONAL_RX_API_URL

    @property
    def national_rx_api_key(self) -> str:
        return self.NATIONAL_RX_API_KEY

    @property
    def national_rx_api_path(self) -> str:
        return self.NATIONAL_RX_API_PATH

    @property
    def national_rx_api_version(self) -> str:
        return self.NATIONAL_RX_API_VERSION

    @property
    def national_rx_timeout(self) -> int:
        return self.NATIONAL_RX_TIMEOUT

    @property
    def bhyt_api_url(self) -> str:
        return self.BHYT_API_URL

    @property
    def bhyt_api_key(self) -> str:
        return self.BHYT_API_KEY

    @property
    def bhyt_api_timeout(self) -> int:
        return self.BHYT_API_TIMEOUT

    class Config:
        """Pydantic config: đọc từ file .env, phân biệt chữ hoa/thường."""

        env_file = ".env"
        case_sensitive = True


settings = Settings()
