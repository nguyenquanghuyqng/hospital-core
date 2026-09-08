"""
CRUD operations cho model :class:`~app.models.user.User`.

Cung cấp các thao tác tra cứu, tạo mới và xác thực tài khoản người dùng.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.user import User
from app.core.security import hash_password, verify_password


class CRUDUser(CRUDBase[User]):
    """
    CRUD class cho User — kế thừa :class:`~app.crud.base.CRUDBase`.

    Bổ sung các thao tác đặc thù: tra cứu theo username,
    tạo user với mật khẩu được hash, và xác thực đăng nhập.
    """

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """
        Tìm người dùng theo tên đăng nhập (username).

        Args:
            db: Async database session.
            username: Tên đăng nhập cần tra cứu.

        Returns:
            :class:`~app.models.user.User` nếu tìm thấy, ``None`` nếu không có.
        """
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        db: AsyncSession,
        *,
        username: str,
        password: str,
        full_name: str,
        role: str = "doctor",
        clinic_room: Optional[str] = None,
    ) -> User:
        """
        Tạo tài khoản người dùng mới với mật khẩu được hash tự động.

        Mật khẩu plain-text được hash bằng bcrypt trước khi lưu vào database.
        Tài khoản mới mặc định có ``is_active=True``.

        Args:
            db: Async database session.
            username: Tên đăng nhập (phải duy nhất trong hệ thống).
            password: Mật khẩu plain-text — sẽ được hash trước khi lưu.
            full_name: Họ tên hiển thị của người dùng.
            role: Vai trò — ``"doctor"`` | ``"nurse"`` | ``"admin"``. Mặc định ``"doctor"``.
            clinic_room: Phòng khám mặc định của bác sĩ (tuỳ chọn).

        Returns:
            :class:`~app.models.user.User` vừa tạo.
        """
        return await self.create(db, obj_in={
            "username":        username,
            "hashed_password": hash_password(password),
            "full_name":       full_name,
            "role":            role,
            "clinic_room":     clinic_room,
            "is_active":       True,
        })

    async def authenticate(
        self, db: AsyncSession, *, username: str, password: str
    ) -> Optional[User]:
        """
        Xác thực thông tin đăng nhập (username + password).

        Tra cứu user theo username, sau đó kiểm tra mật khẩu bằng bcrypt.

        Args:
            db: Async database session.
            username: Tên đăng nhập.
            password: Mật khẩu plain-text cần kiểm tra.

        Returns:
            :class:`~app.models.user.User` nếu thông tin hợp lệ.
            ``None`` nếu username không tồn tại hoặc mật khẩu sai.
        """
        user = await self.get_by_username(db, username)
        if user and verify_password(password, user.hashed_password):
            return user
        return None


crud_user = CRUDUser(User)
"""Singleton instance của :class:`CRUDUser` dùng toàn ứng dụng."""
