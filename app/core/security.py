"""
Tiện ích bảo mật: hash mật khẩu + tạo/xác minh JWT.

Cung cấp các hàm độc lập (không phụ thuộc framework) để:
- Hash và kiểm tra mật khẩu bằng bcrypt.
- Tạo và giải mã JWT access token bằng python-jose.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
import bcrypt

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """
    Hash mật khẩu plain-text bằng bcrypt.

    Args:
        plain: Mật khẩu dạng văn bản thường.

    Returns:
        Chuỗi hash bcrypt đã encode (UTF-8 string).
    """
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """
    Kiểm tra mật khẩu plain-text có khớp với hash bcrypt không.

    Args:
        plain: Mật khẩu người dùng nhập vào.
        hashed: Chuỗi hash bcrypt lưu trong database.

    Returns:
        True nếu khớp, False nếu không.
    """
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Tạo JWT access token với thời gian hết hạn.

    Args:
        data: Payload cần mã hoá vào token (thường chứa ``{"sub": user_id}``).
        expires_delta: Thời gian sống tuỳ chỉnh. Nếu None, dùng giá trị mặc định
            từ ``settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES``.

    Returns:
        Chuỗi JWT đã ký.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Giải mã và xác minh chữ ký JWT.

    Args:
        token: Chuỗi JWT cần giải mã.

    Returns:
        Dict payload nếu token hợp lệ và chưa hết hạn.
        None nếu token không hợp lệ, hết hạn, hoặc sai chữ ký.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
