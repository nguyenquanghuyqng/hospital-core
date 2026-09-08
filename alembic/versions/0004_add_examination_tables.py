"""add examination, diagnoses, prescription_items tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-07 12:00:00.000000

Thêm:
- examination_status  ENUM
- disposition_type    ENUM
- payment_type        ENUM
- examinations        TABLE
- diagnoses           TABLE
- prescription_items  TABLE
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

from app.models.enums import ExaminationStatus, DispositionType, PaymentType

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EXAM_STATUS_VALUES = ", ".join(f"'{s.value}'" for s in ExaminationStatus)
_DISP_TYPE_VALUES   = ", ".join(f"'{s.value}'" for s in DispositionType)
_PAY_TYPE_VALUES    = ", ".join(f"'{s.value}'" for s in PaymentType)


def upgrade() -> None:
    # ── Enum types ────────────────────────────────────────────────────────────
    op.execute(f"CREATE TYPE examination_status AS ENUM ({_EXAM_STATUS_VALUES})")
    op.execute(f"CREATE TYPE disposition_type   AS ENUM ({_DISP_TYPE_VALUES})")
    op.execute(f"CREATE TYPE payment_type       AS ENUM ({_PAY_TYPE_VALUES})")

    # ── examinations ──────────────────────────────────────────────────────────
    op.create_table(
        "examinations",
        sa.Column("id",           sa.Integer(), nullable=False),
        sa.Column("reception_id", sa.Integer(), sa.ForeignKey("receptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id",   sa.Integer(), sa.ForeignKey("patients.id",   ondelete="CASCADE"), nullable=False),
        sa.Column("doctor_id",    sa.Integer(), sa.ForeignKey("users.id",      ondelete="SET NULL"), nullable=True),

        # Status — tạo bằng String trước, ALTER sau
        sa.Column("status",       sa.String(20), nullable=False, server_default=ExaminationStatus.DRAFT.value),

        # Khung II — thông tin vào
        sa.Column("exam_date",     sa.Date(),  server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("exam_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exam_end_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("exam_end_date", sa.Date(),  nullable=True),
        sa.Column("subject_type",  sa.String(10),  nullable=True),
        sa.Column("subject_name",  sa.String(100), nullable=True),
        sa.Column("insurance_number",     sa.String(20), nullable=True),
        sa.Column("insurance_valid_from", sa.Date(),     nullable=True),
        sa.Column("insurance_valid_to",   sa.Date(),     nullable=True),
        sa.Column("referral_from_type",   sa.String(100), nullable=True),
        sa.Column("referral_from_name",   sa.String(200), nullable=True),
        sa.Column("referral_diagnosis",   sa.Text(),      nullable=True),
        sa.Column("clinical_symptoms",    sa.Text(),      nullable=True),

        # Khung III — thông tin khám
        sa.Column("doctor_name",  sa.String(100), nullable=True),
        sa.Column("nurse_name",   sa.String(100), nullable=True),
        sa.Column("complications", sa.Text(),     nullable=True),

        # Disposition — String trước, ALTER sau
        sa.Column("disposition",  sa.String(30), nullable=True),

        sa.Column("revisit_days",   sa.Integer(),    nullable=True),
        sa.Column("revisit_result", sa.String(50),   nullable=True),
        sa.Column("transfer_to_facility", sa.String(200), nullable=True),
        sa.Column("transfer_reason",      sa.Text(),      nullable=True),
        sa.Column("admit_ward",           sa.String(100), nullable=True),
        sa.Column("admit_priority",  sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_near_poor",    sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_poor",         sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("flag_priority",   sa.Boolean(), nullable=False, server_default=sa.text("false")),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reception_id"),
    )
    op.create_index(op.f("ix_examinations_id"),           "examinations", ["id"])
    op.create_index(op.f("ix_examinations_reception_id"), "examinations", ["reception_id"])
    op.create_index(op.f("ix_examinations_patient_id"),   "examinations", ["patient_id"])
    op.create_index(op.f("ix_examinations_doctor_id"),    "examinations", ["doctor_id"])

    # ALTER status → native enum
    op.execute("ALTER TABLE examinations ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE examinations ALTER COLUMN status TYPE examination_status USING status::examination_status")
    op.execute(f"ALTER TABLE examinations ALTER COLUMN status SET DEFAULT '{ExaminationStatus.DRAFT.value}'::examination_status")

    # ALTER disposition → native enum (nullable)
    op.execute("ALTER TABLE examinations ALTER COLUMN disposition TYPE disposition_type USING disposition::disposition_type")

    # ── diagnoses ──────────────────────────────────────────────────────────────
    op.create_table(
        "diagnoses",
        sa.Column("id",             sa.Integer(), nullable=False),
        sa.Column("examination_id", sa.Integer(), sa.ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("icd_code",   sa.String(20),  nullable=True),
        sa.Column("icd_name",   sa.String(300), nullable=False),
        sa.Column("is_primary", sa.Boolean(),   nullable=False, server_default=sa.text("false")),
        sa.Column("note",       sa.Text(),      nullable=True),
        sa.Column("sort_order", sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_diagnoses_id"),             "diagnoses", ["id"])
    op.create_index(op.f("ix_diagnoses_examination_id"), "diagnoses", ["examination_id"])

    # ── prescription_items ────────────────────────────────────────────────────
    op.create_table(
        "prescription_items",
        sa.Column("id",             sa.Integer(), nullable=False),
        sa.Column("examination_id", sa.Integer(), sa.ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type",  sa.String(10),   nullable=False, server_default="drug"),
        sa.Column("item_code",  sa.String(50),   nullable=True),
        sa.Column("item_name",  sa.String(300),  nullable=False),
        sa.Column("unit",       sa.String(30),   nullable=True),
        sa.Column("quantity",   sa.Numeric(10,2),nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(15,2),nullable=True),
        sa.Column("usage_instruction", sa.Text(),       nullable=True),
        sa.Column("valid_from", sa.Date(),       nullable=True),
        sa.Column("valid_to",   sa.Date(),       nullable=True),
        # payment_type — String trước
        sa.Column("payment_type", sa.String(20), nullable=False, server_default=PaymentType.BHYT.value),
        sa.Column("total_amount",   sa.Numeric(15,2), nullable=True),
        sa.Column("bhyt_amount",    sa.Numeric(15,2), nullable=True),
        sa.Column("patient_amount", sa.Numeric(15,2), nullable=True),
        sa.Column("room_name",   sa.String(50),  nullable=True),
        sa.Column("doctor_name", sa.String(100), nullable=True),
        sa.Column("sort_order",  sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prescription_items_id"),             "prescription_items", ["id"])
    op.create_index(op.f("ix_prescription_items_examination_id"), "prescription_items", ["examination_id"])

    # ALTER payment_type → native enum
    op.execute("ALTER TABLE prescription_items ALTER COLUMN payment_type DROP DEFAULT")
    op.execute("ALTER TABLE prescription_items ALTER COLUMN payment_type TYPE payment_type USING payment_type::payment_type")
    op.execute(f"ALTER TABLE prescription_items ALTER COLUMN payment_type SET DEFAULT '{PaymentType.BHYT.value}'::payment_type")


def downgrade() -> None:
    op.drop_table("prescription_items")
    op.drop_table("diagnoses")
    op.drop_table("examinations")
    op.execute("DROP TYPE IF EXISTS payment_type")
    op.execute("DROP TYPE IF EXISTS disposition_type")
    op.execute("DROP TYPE IF EXISTS examination_status")
