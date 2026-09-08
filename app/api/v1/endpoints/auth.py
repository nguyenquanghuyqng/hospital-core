"""
Auth endpoints — xác thực và quản lý tài khoản.

Routes:
  POST /auth/login    — đăng nhập, trả JWT access token
  GET  /auth/me       — thông tin tài khoản đang đăng nhập
  POST /auth/register — tạo tài khoản mới
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import create_access_token
from app.core.deps import get_current_user
from app.crud.user import crud_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth - Xác thực"])


# ── Local schemas ─────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """
    Response trả về sau khi đăng nhập thành công.

    Attributes:
        access_token: JWT Bearer token dùng để xác thực các request tiếp theo.
        token_type: Luôn là ``"bearer"``.
        user_id: ID người dùng đang đăng nhập.
        username: Tên đăng nhập.
        full_name: Họ tên hiển thị (có thể None).
        role: Vai trò — ``"doctor"`` | ``"nurse"`` | ``"admin"``.
        clinic_room: Phòng khám mặc định (có thể None).
    """

    access_token: str
    token_type:   str = "bearer"
    user_id:      int
    username:     str
    full_name:    Optional[str]
    role:         str
    clinic_room:  Optional[str]


class UserResponse(BaseModel):
    """
    Response thông tin tài khoản người dùng.

    Dùng cho endpoint ``GET /auth/me`` và ``POST /auth/register``.

    Attributes:
        id: ID người dùng.
        username: Tên đăng nhập.
        full_name: Họ tên hiển thị.
        role: Vai trò trong hệ thống.
        clinic_room: Phòng khám mặc định.
        is_active: Trạng thái hoạt động của tài khoản.
    """

    id:          int
    username:    str
    full_name:   Optional[str]
    role:        str
    clinic_room: Optional[str]
    is_active:   bool

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    """
    Body request tạo tài khoản mới.

    Attributes:
        username: Tên đăng nhập (phải duy nhất).
        password: Mật khẩu plain-text — server sẽ hash trước khi lưu.
        full_name: Họ tên hiển thị (tuỳ chọn, mặc định = username).
        role: Vai trò — mặc định ``"doctor"``.
        clinic_room: Phòng khám mặc định (tuỳ chọn).
    """

    username:    str
    password:    str
    full_name:   Optional[str] = None
    role:        str = "doctor"
    clinic_room: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Đăng nhập")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Xác thực thông tin đăng nhập và trả về JWT access token.

    Nhận dữ liệu dạng ``application/x-www-form-urlencoded`` (OAuth2 standard):
    ``username`` và ``password``.

    Args:
        form_data: Form data chứa ``username`` và ``password``.
        db: Async database session (injected).

    Returns:
        :class:`TokenResponse` chứa ``access_token`` và thông tin user.

    Raises:
        HTTPException 401: Sai tên đăng nhập hoặc mật khẩu.
        HTTPException 403: Tài khoản đã bị vô hiệu hoá.
    """
    user = await crud_user.authenticate(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị vô hiệu hoá")

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        clinic_room=user.clinic_room,
    )


@router.get("/me", response_model=UserResponse, summary="Thông tin tài khoản hiện tại")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Trả về thông tin tài khoản của người dùng đang đăng nhập.

    Yêu cầu Bearer token hợp lệ trong header ``Authorization``.

    Args:
        current_user: User đang đăng nhập (injected từ JWT token).

    Returns:
        :class:`UserResponse` với thông tin tài khoản hiện tại.
    """
    return current_user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo tài khoản mới",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo tài khoản người dùng mới trong hệ thống.

    Mật khẩu được hash tự động trước khi lưu vào database.

    Note:
        Trong môi trường production nên bảo vệ endpoint này bằng admin token.
        Hiện tại để mở để dễ seed data ban đầu.

    Args:
        body: :class:`RegisterRequest` chứa thông tin tài khoản cần tạo.
        db: Async database session (injected).

    Returns:
        :class:`UserResponse` của tài khoản vừa tạo.

    Raises:
        HTTPException 409: Username đã tồn tại trong hệ thống.
    """
    existing = await crud_user.get_by_username(db, body.username)
    if existing:
        raise HTTPException(status_code=409, detail=f"Username '{body.username}' đã tồn tại")

    user = await crud_user.create_user(
        db,
        username=body.username,
        password=body.password,
        full_name=body.full_name or body.username,
        role=body.role,
        clinic_room=body.clinic_room,
    )
    return user
