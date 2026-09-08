"""add visit_status to receptions and users table for auth

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-07 10:00:00.000000

Thêm:
- visit_status column vào receptions (Chờ khám / CLS / Có KQ / Tái khám / Xong)
- Bảng users (id, username, hashed_password, full_name, role, clinic_room, is_active)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.enums import VisitStatus

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VISIT_STATUS_VALUES = ", ".join(f"'{s.value}'" for s in VisitStatus)


def upgrade() -> None:
    # ── Tạo PostgreSQL native TYPE ────────────────────────────────────
    op.execute(f"CREATE TYPE visit_status AS ENUM ({_VISIT_STATUS_VALUES})")

    # ── Thêm cột visit_status vào receptions ─────────────────────────
    op.add_column(
        "receptions",
        sa.Column("visit_status", sa.String(20), nullable=False, server_default=VisitStatus.WAITING.value),
    )
    # Đổi sang native enum
    op.execute("ALTER TABLE receptions ALTER COLUMN visit_status DROP DEFAULT")
    op.execute(
        "ALTER TABLE receptions "
        "ALTER COLUMN visit_status TYPE visit_status USING visit_status::visit_status"
    )
    op.execute(
        f"ALTER TABLE receptions ALTER COLUMN visit_status "
        f"SET DEFAULT '{VisitStatus.WAITING.value}'::visit_status"
    )

    # ── Bảng users ────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",              sa.Integer(),    nullable=False),
        sa.Column("username",        sa.String(50),   nullable=False, comment="Tên đăng nhập"),
        sa.Column("hashed_password", sa.String(200),  nullable=False),
        sa.Column("full_name",       sa.String(100),  nullable=True,  comment="Họ tên hiển thị"),
        sa.Column("role",            sa.String(20),   nullable=False, server_default="doctor",
                  comment="doctor | nurse | admin"),
        sa.Column("clinic_room",     sa.String(50),   nullable=True,  comment="Phòng khám phụ trách"),
        sa.Column("is_active",       sa.Boolean(),    nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"),       "users", ["id"])
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_table("users")
    op.drop_column("receptions", "visit_status")
    op.execute("DROP TYPE IF EXISTS visit_status")
