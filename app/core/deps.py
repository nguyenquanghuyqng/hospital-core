"""
FastAPI dependencies dùng chung cho tất cả endpoints.

Phân quyền theo 5 vai trò:
  doctor      — bác sĩ: khám bệnh, kê đơn, chỉ định CLS
  nurse       — điều dưỡng: ghi vital signs, hỗ trợ khám
  receptionist— lễ tân: tiếp đón, hồ sơ bệnh nhân, hàng đợi
  cashier     — thu ngân: viện phí, thanh toán, hóa đơn
  admin       — quản trị: toàn quyền

Ma trận quyền:
  require_doctor        → doctor | admin
  require_nurse         → nurse | doctor | admin
  require_receptionist  → receptionist | admin
  require_cashier       → cashier | admin
  require_clinical      → doctor | nurse | admin          (mọi lâm sàng)
  require_admin         → admin only
  get_current_user      → mọi role đã xác thực
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ── Role sets ─────────────────────────────────────────────────────────────────
_ALL_ROLES          = frozenset({"doctor", "nurse", "receptionist", "cashier", "admin"})
_DOCTOR_ROLES       = frozenset({"doctor", "admin"})
_NURSE_ROLES        = frozenset({"nurse", "doctor", "admin"})
_CLINICAL_ROLES     = frozenset({"doctor", "nurse", "admin"})
_RECEPTIONIST_ROLES = frozenset({"receptionist", "admin"})
_CASHIER_ROLES      = frozenset({"cashier", "admin"})
_ADMIN_ROLES        = frozenset({"admin"})


# ── Base auth ─────────────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency cơ bản: xác thực Bearer JWT, trả về user đang đăng nhập.
    Dùng cho mọi endpoint yêu cầu đăng nhập (bất kể role).
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exc

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc
    return user


# ── Role-specific dependencies ────────────────────────────────────────────────

def _make_require(allowed: frozenset, label: str):
    """Factory tạo dependency kiểm tra role, tránh lặp code."""
    async def _require(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quyền truy cập yêu cầu: {label}",
            )
        return current_user
    _require.__name__ = f"require_{label}"
    return _require


require_doctor       = _make_require(_DOCTOR_ROLES,       "doctor / admin")
require_nurse        = _make_require(_NURSE_ROLES,        "nurse / doctor / admin")
require_clinical     = _make_require(_CLINICAL_ROLES,     "doctor / nurse / admin")
require_receptionist = _make_require(_RECEPTIONIST_ROLES, "receptionist / admin")
require_cashier      = _make_require(_CASHIER_ROLES,      "cashier / admin")
require_admin        = _make_require(_ADMIN_ROLES,        "admin")
