from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.user import User
from app.core.security import hash_password, verify_password


class CRUDUser(CRUDBase[User]):

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
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
        user = await self.get_by_username(db, username)
        if user and verify_password(password, user.hashed_password):
            return user
        return None


crud_user = CRUDUser(User)
