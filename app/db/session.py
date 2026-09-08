"""
Khởi tạo database engine và session factory.

Cung cấp hai engine riêng biệt:
- **Async engine** (asyncpg): dùng trong FastAPI request lifecycle.
- **Sync engine** (psycopg2): dùng trong Alembic migration script.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# ── Async engine — dùng cho FastAPI ──────────────────────────────────────────
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,       # In SQL ra log khi DEBUG=True
    pool_pre_ping=True,        # Kiểm tra kết nối trước khi dùng
    pool_size=10,              # Số kết nối tối thiểu trong pool
    max_overflow=20,           # Số kết nối bổ sung tối đa khi pool đầy
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,    # Giữ nguyên object sau commit (không lazy-reload)
    autocommit=False,
    autoflush=False,
)

# ── Sync engine — dùng cho Alembic migrations ────────────────────────────────
sync_engine = create_engine(
    settings.DATABASE_SYNC_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    FastAPI dependency: cung cấp async database session cho mỗi request.

    Luồng xử lý:
    - Mở session mới từ ``AsyncSessionLocal``.
    - ``yield`` session cho endpoint sử dụng.
    - Commit tự động khi endpoint xử lý thành công.
    - Rollback tự động nếu có exception bất kỳ.
    - Đóng session trong mọi trường hợp (finally).

    Yields:
        :class:`AsyncSession`: Session đã sẵn sàng thực thi query.

    Note:
        CRUD operations chỉ gọi ``flush()`` chứ không ``commit()``
        trực tiếp — commit được uỷ quyền cho hàm này.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
