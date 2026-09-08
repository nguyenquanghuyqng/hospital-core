"""
Auth endpoints.

Routes:
  POST /auth/login   — đăng nhập, trả JWT
  GET  /auth/me      — thông tin user hiện tại
  POST /auth/register — tạo tài khoản (admin only hoặc seed)
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


# ── Schemas ───────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id:    int
    username:   str
    full_name:  Optional[str]
    role:       str
    clinic_room: Optional[str]


class UserResponse(BaseModel):
    id:          int
    username:    str
    full_name:   Optional[str]
    role:        str
    clinic_room: Optional[str]
    is_active:   bool

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
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
    Tạo tài khoản. Trong môi trường production nên bảo vệ endpoint này
    bằng admin token. Hiện tại để mở để dễ seed data.
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
