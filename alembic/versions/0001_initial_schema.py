"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-07 00:00:00.000000

Tạo 3 bảng cơ bản: patients, queue_tickets, receptions.

Quy tắc enum trong migration:
- Enum PostgreSQL TYPE tạo/xoá bằng raw SQL (IF NOT EXISTS / IF EXISTS).
- Column status khai báo là sa.String với CHECK constraint —
  tránh hoàn toàn việc dùng sa.Enum trong migration để không bị
  SQLAlchemy trigger thêm CREATE TYPE.
- server_default lấy từ enum class, không hardcode string.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.enums import QueueStatus, ReceptionStatus

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Giá trị enum lấy từ class, không hardcode ────────────────────────────────
_QUEUE_STATUS_VALUES    = ", ".join(f"'{s.value}'" for s in QueueStatus)
_RECEPTION_STATUS_VALUES = ", ".join(f"'{s.value}'" for s in ReceptionStatus)


def upgrade() -> None:
    # ── Tạo PostgreSQL native TYPE bằng raw SQL ───────────────────────────────
    op.execute(
        f"CREATE TYPE queue_status AS ENUM ({_QUEUE_STATUS_VALUES})"
    )
    op.execute(
        f"CREATE TYPE reception_status AS ENUM ({_RECEPTION_STATUS_VALUES})"
    )

    # ── patients ──────────────────────────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id",            sa.Integer(),  nullable=False),
        sa.Column("cccd",          sa.String(12), nullable=True,  comment="Số CCCD/CMND"),
        sa.Column("full_name",     sa.String(100),nullable=False, comment="Họ và tên"),
        sa.Column("date_of_birth", sa.Date(),     nullable=True,  comment="Ngày sinh"),
        sa.Column("gender",        sa.String(10), nullable=True,  comment="Giới tính"),
        sa.Column("address",       sa.Text(),     nullable=True,  comment="Địa chỉ"),
        sa.Column("phone",         sa.String(15), nullable=True),
        sa.Column("email",         sa.String(100),nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patients_id"),   "patients", ["id"])
    op.create_index(op.f("ix_patients_cccd"), "patients", ["cccd"], unique=True)

    # ── queue_tickets ─────────────────────────────────────────────────────────
    # status dùng cast sang native type đã tạo ở trên
    op.create_table(
        "queue_tickets",
        sa.Column("id",            sa.Integer(),  nullable=False),
        sa.Column("ticket_number", sa.String(10), nullable=False, comment="Số thứ tự"),
        sa.Column("sequence",      sa.Integer(),  nullable=False),
        sa.Column("issue_date",    sa.Date(),     server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=QueueStatus.WAITING.value,
        ),
        sa.Column("service_type",   sa.String(50),              nullable=True),
        sa.Column("counter_number", sa.Integer(),               nullable=True),
        sa.Column("called_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("served_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("done_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("note",           sa.Text(),                  nullable=True),
        sa.Column("patient_id",     sa.Integer(),
                  sa.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Đổi column type sang native enum: drop default → cast → set lại default
    op.execute("ALTER TABLE queue_tickets ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE queue_tickets "
        "ALTER COLUMN status TYPE queue_status USING status::queue_status"
    )
    op.execute(
        f"ALTER TABLE queue_tickets ALTER COLUMN status "
        f"SET DEFAULT '{QueueStatus.WAITING.value}'::queue_status"
    )
    op.create_index(op.f("ix_queue_tickets_id"),            "queue_tickets", ["id"])
    op.create_index(op.f("ix_queue_tickets_ticket_number"), "queue_tickets", ["ticket_number"])
    op.create_index(op.f("ix_queue_tickets_patient_id"),    "queue_tickets", ["patient_id"])

    # ── receptions ────────────────────────────────────────────────────────────
    op.create_table(
        "receptions",
        sa.Column("id",         sa.Integer(), nullable=False),
        sa.Column("visit_date", sa.Date(),    server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=ReceptionStatus.PENDING.value,
        ),
        sa.Column("reason",            sa.Text(),       nullable=True),
        sa.Column("department",        sa.String(100),  nullable=True),
        sa.Column("doctor_name",       sa.String(100),  nullable=True),
        sa.Column("priority",          sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("insurance_number",  sa.String(20),   nullable=True),
        sa.Column("insurance_expiry",  sa.Date(),       nullable=True),
        sa.Column("checked_in_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("receptionist_name", sa.String(100),  nullable=True),
        sa.Column("internal_note",     sa.Text(),       nullable=True),
        sa.Column("patient_id",        sa.Integer(),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("queue_ticket_id",   sa.Integer(),
                  sa.ForeignKey("queue_tickets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("queue_ticket_id"),
    )
    op.execute("ALTER TABLE receptions ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE receptions "
        "ALTER COLUMN status TYPE reception_status USING status::reception_status"
    )
    op.execute(
        f"ALTER TABLE receptions ALTER COLUMN status "
        f"SET DEFAULT '{ReceptionStatus.PENDING.value}'::reception_status"
    )
    op.create_index(op.f("ix_receptions_id"),              "receptions", ["id"])
    op.create_index(op.f("ix_receptions_patient_id"),      "receptions", ["patient_id"])
    op.create_index(op.f("ix_receptions_queue_ticket_id"), "receptions", ["queue_ticket_id"])


def downgrade() -> None:
    op.drop_table("receptions")
    op.drop_table("queue_tickets")
    op.drop_table("patients")
    op.execute("DROP TYPE IF EXISTS reception_status")
    op.execute("DROP TYPE IF EXISTS queue_status")
