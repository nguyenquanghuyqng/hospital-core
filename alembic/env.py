"""
Alembic migration environment.

Quy tắc enum:
- Enum PostgreSQL TYPE được tạo hoàn toàn bởi migration scripts bằng raw SQL.
- Model dùng native_enum=False ở runtime để tránh SQLAlchemy tự phát sinh
  CREATE TYPE ngoài migration context.
- env.py KHÔNG import Base.metadata để tránh event listener tự create enum.
  Thay vào đó dùng MetaData riêng chỉ cho autogenerate.
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, MetaData
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_SYNC_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base sau khi đã configure để đăng ký models
from app.db.base import Base  # noqa: E402, F401
target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """Loại trừ PostgreSQL named TYPE khỏi autogenerate — migration quản lý thủ công."""
    if type_ == "type":
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
