"""add cls_results, bills, payments, appointments

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-09 12:00:00.000000

Tạo 6 bảng mới:
  - cls_results           — phiếu kết quả CLS (1-1 với prescription_items CLS)
  - cls_result_values     — từng chỉ số kết quả (HGB, WBC...)
  - bills                 — hóa đơn viện phí
  - bill_items            — dòng chi phí trong hóa đơn
  - payments              — giao dịch thanh toán
  - appointments          — lịch hẹn khám

Thêm 4 PostgreSQL native ENUM types:
  - cls_result_status
  - bill_status
  - payment_method
  - appointment_status

Không phá vỡ dữ liệu hiện có.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.enums import (
    ClsResultStatus, BillStatus, PaymentMethod, AppointmentStatus,
    PaymentType,
)

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CLS_RESULT_STATUS_VALUES = ", ".join(f"'{s.value}'" for s in ClsResultStatus)
_BILL_STATUS_VALUES       = ", ".join(f"'{s.value}'" for s in BillStatus)
_PAYMENT_METHOD_VALUES    = ", ".join(f"'{s.value}'" for s in PaymentMethod)
_APPT_STATUS_VALUES       = ", ".join(f"'{s.value}'" for s in AppointmentStatus)


def upgrade() -> None:
    # ── Tạo PostgreSQL native TYPE ────────────────────────────────────────────
    op.execute(f"CREATE TYPE cls_result_status AS ENUM ({_CLS_RESULT_STATUS_VALUES})")
    op.execute(f"CREATE TYPE bill_status       AS ENUM ({_BILL_STATUS_VALUES})")
    op.execute(f"CREATE TYPE payment_method    AS ENUM ({_PAYMENT_METHOD_VALUES})")
    op.execute(f"CREATE TYPE appointment_status AS ENUM ({_APPT_STATUS_VALUES})")

    # ── cls_results ───────────────────────────────────────────────────────────
    op.create_table(
        "cls_results",
        sa.Column("id",                   sa.Integer(),    nullable=False),
        sa.Column("prescription_item_id", sa.Integer(),
                  sa.ForeignKey("prescription_items.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("examination_id", sa.Integer(),
                  sa.ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id",     sa.Integer(),
                  sa.ForeignKey("patients.id",     ondelete="CASCADE"), nullable=False),
        sa.Column("service_code",   sa.String(30),   nullable=True),
        sa.Column("service_name",   sa.String(300),  nullable=False),
        sa.Column("department",     sa.String(100),  nullable=True),
        sa.Column("status",         sa.String(20),   nullable=False,
                  server_default=ClsResultStatus.PENDING.value),
        sa.Column("performed_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("performed_by",   sa.String(100),  nullable=True),
        sa.Column("verified_by",    sa.String(100),  nullable=True),
        sa.Column("result_summary", sa.Text(),        nullable=True),
        sa.Column("result_note",    sa.Text(),        nullable=True),
        sa.Column("result_file_url",sa.String(500),  nullable=True),
        sa.Column("is_abnormal",    sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("ALTER TABLE cls_results ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE cls_results "
        "ALTER COLUMN status TYPE cls_result_status USING status::cls_result_status"
    )
    op.execute(
        f"ALTER TABLE cls_results ALTER COLUMN status "
        f"SET DEFAULT '{ClsResultStatus.PENDING.value}'::cls_result_status"
    )
    op.create_index("ix_cls_results_id",                   "cls_results", ["id"])
    op.create_index("ix_cls_results_prescription_item_id", "cls_results", ["prescription_item_id"], unique=True)
    op.create_index("ix_cls_results_examination_id",       "cls_results", ["examination_id"])
    op.create_index("ix_cls_results_patient_id",           "cls_results", ["patient_id"])
    op.create_index("ix_cls_results_status",               "cls_results", ["status"])

    # ── cls_result_values ─────────────────────────────────────────────────────
    op.create_table(
        "cls_result_values",
        sa.Column("id",             sa.Integer(),       nullable=False),
        sa.Column("cls_result_id",  sa.Integer(),
                  sa.ForeignKey("cls_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("indicator_name", sa.String(100),     nullable=False),
        sa.Column("indicator_code", sa.String(50),      nullable=True),
        sa.Column("value_text",     sa.String(200),     nullable=True),
        sa.Column("value_numeric",  sa.Numeric(15, 4),  nullable=True),
        sa.Column("unit",           sa.String(50),      nullable=True),
        sa.Column("ref_min",        sa.Numeric(15, 4),  nullable=True),
        sa.Column("ref_max",        sa.Numeric(15, 4),  nullable=True),
        sa.Column("ref_text",       sa.String(100),     nullable=True),
        sa.Column("is_abnormal",    sa.Boolean(),       nullable=False, server_default="false"),
        sa.Column("sort_order",     sa.Integer(),       nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cls_result_values_id",            "cls_result_values", ["id"])
    op.create_index("ix_cls_result_values_cls_result_id", "cls_result_values", ["cls_result_id"])

    # ── bills ─────────────────────────────────────────────────────────────────
    op.create_table(
        "bills",
        sa.Column("id",               sa.Integer(),     nullable=False),
        sa.Column("bill_number",      sa.String(30),    nullable=False),
        sa.Column("examination_id",   sa.Integer(),
                  sa.ForeignKey("examinations.id", ondelete="SET NULL"), nullable=True, unique=True),
        sa.Column("patient_id",       sa.Integer(),
                  sa.ForeignKey("patients.id",    ondelete="SET NULL"), nullable=True),
        sa.Column("reception_id",     sa.Integer(),
                  sa.ForeignKey("receptions.id",  ondelete="SET NULL"), nullable=True),
        sa.Column("status",           sa.String(20),    nullable=False,
                  server_default=BillStatus.DRAFT.value),
        sa.Column("issued_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("cashier_id",       sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cashier_name",     sa.String(100),   nullable=True),
        sa.Column("drug_total",       sa.Numeric(15, 2),nullable=False, server_default="0"),
        sa.Column("cls_total",        sa.Numeric(15, 2),nullable=False, server_default="0"),
        sa.Column("service_total",    sa.Numeric(15, 2),nullable=False, server_default="0"),
        sa.Column("grand_total",      sa.Numeric(15, 2),nullable=False, server_default="0"),
        sa.Column("bhyt_pays",        sa.Numeric(15, 2),nullable=False, server_default="0"),
        sa.Column("patient_pays",     sa.Numeric(15, 2),nullable=False, server_default="0"),
        sa.Column("discount_amount",  sa.Numeric(15, 2),nullable=False, server_default="0"),
        sa.Column("deposit_amount",   sa.Numeric(15, 2),nullable=False, server_default="0"),
        sa.Column("balance_due",      sa.Numeric(15, 2),nullable=False, server_default="0"),
        sa.Column("insurance_number", sa.String(20),    nullable=True),
        sa.Column("bhyt_contract_no", sa.String(50),    nullable=True),
        sa.Column("bhyt_approved_code", sa.String(50),  nullable=True),
        sa.Column("note",             sa.Text(),         nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bill_number"),
    )
    op.execute("ALTER TABLE bills ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE bills ALTER COLUMN status TYPE bill_status USING status::bill_status")
    op.execute(f"ALTER TABLE bills ALTER COLUMN status SET DEFAULT '{BillStatus.DRAFT.value}'::bill_status")
    op.create_index("ix_bills_id",             "bills", ["id"])
    op.create_index("ix_bills_bill_number",    "bills", ["bill_number"], unique=True)
    op.create_index("ix_bills_examination_id", "bills", ["examination_id"], unique=True)
    op.create_index("ix_bills_patient_id",     "bills", ["patient_id"])
    op.create_index("ix_bills_status",         "bills", ["status"])

    # ── bill_items ────────────────────────────────────────────────────────────
    op.create_table(
        "bill_items",
        sa.Column("id",                   sa.Integer(),      nullable=False),
        sa.Column("bill_id",              sa.Integer(),
                  sa.ForeignKey("bills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prescription_item_id", sa.Integer(),
                  sa.ForeignKey("prescription_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_type",    sa.String(10),      nullable=False, server_default="drug"),
        sa.Column("item_code",    sa.String(50),      nullable=True),
        sa.Column("item_name",    sa.String(300),     nullable=False),
        sa.Column("unit",         sa.String(30),      nullable=True),
        sa.Column("quantity",     sa.Numeric(10, 2),  nullable=False, server_default="1"),
        sa.Column("unit_price",   sa.Numeric(15, 2),  nullable=True),
        sa.Column("payment_type", sa.String(20),      nullable=False, server_default=PaymentType.BHYT.value),
        sa.Column("total_amount",   sa.Numeric(15, 2),nullable=True),
        sa.Column("bhyt_amount",    sa.Numeric(15, 2),nullable=True),
        sa.Column("patient_amount", sa.Numeric(15, 2),nullable=True),
        sa.Column("sort_order",     sa.Integer(),     nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bill_items_id",      "bill_items", ["id"])
    op.create_index("ix_bill_items_bill_id", "bill_items", ["bill_id"])
    # Đổi payment_type column sang native enum
    op.execute("ALTER TABLE bill_items ALTER COLUMN payment_type DROP DEFAULT")
    op.execute("ALTER TABLE bill_items ALTER COLUMN payment_type TYPE payment_type USING payment_type::payment_type")
    op.execute(f"ALTER TABLE bill_items ALTER COLUMN payment_type SET DEFAULT '{PaymentType.BHYT.value}'::payment_type")

    # ── payments ──────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id",             sa.Integer(),      nullable=False),
        sa.Column("bill_id",        sa.Integer(),
                  sa.ForeignKey("bills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cashier_id",     sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payment_method", sa.String(20),     nullable=False,
                  server_default=PaymentMethod.CASH.value),
        sa.Column("amount",         sa.Numeric(15, 2), nullable=False),
        sa.Column("paid_at",        sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("transaction_ref",sa.String(100),    nullable=True),
        sa.Column("note",           sa.Text(),          nullable=True),
        sa.Column("is_deposit",     sa.Boolean(),      nullable=False, server_default="false"),
        sa.Column("is_refund",      sa.Boolean(),      nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("ALTER TABLE payments ALTER COLUMN payment_method DROP DEFAULT")
    op.execute("ALTER TABLE payments ALTER COLUMN payment_method TYPE payment_method USING payment_method::payment_method")
    op.execute(f"ALTER TABLE payments ALTER COLUMN payment_method SET DEFAULT '{PaymentMethod.CASH.value}'::payment_method")
    op.create_index("ix_payments_id",      "payments", ["id"])
    op.create_index("ix_payments_bill_id", "payments", ["bill_id"])
    op.create_index("ix_payments_paid_at", "payments", ["paid_at"])

    # ── appointments ──────────────────────────────────────────────────────────
    op.create_table(
        "appointments",
        sa.Column("id",               sa.Integer(),    nullable=False),
        sa.Column("appointment_no",   sa.String(20),   nullable=False),
        sa.Column("patient_id",       sa.Integer(),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doctor_id",        sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("examination_id",   sa.Integer(),
                  sa.ForeignKey("examinations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scheduled_date",   sa.Date(),       nullable=False),
        sa.Column("scheduled_time",   sa.String(10),   nullable=True),
        sa.Column("status",           sa.String(20),   nullable=False,
                  server_default=AppointmentStatus.SCHEDULED.value),
        sa.Column("appointment_type", sa.String(20),   nullable=False, server_default="'new'"),
        sa.Column("reason",           sa.Text(),        nullable=True),
        sa.Column("doctor_name",      sa.String(100),  nullable=True),
        sa.Column("department",       sa.String(100),  nullable=True),
        sa.Column("clinic_room",      sa.String(50),   nullable=True),
        sa.Column("note",             sa.Text(),        nullable=True),
        sa.Column("patient_note",     sa.Text(),        nullable=True),
        sa.Column("created_by",       sa.String(100),  nullable=True),
        sa.Column("confirmed_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason",    sa.Text(),        nullable=True),
        sa.Column("is_reminded",      sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("appointment_no"),
    )
    op.execute("ALTER TABLE appointments ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE appointments ALTER COLUMN status TYPE appointment_status USING status::appointment_status")
    op.execute(
        f"ALTER TABLE appointments ALTER COLUMN status "
        f"SET DEFAULT '{AppointmentStatus.SCHEDULED.value}'::appointment_status"
    )
    op.create_index("ix_appointments_id",             "appointments", ["id"])
    op.create_index("ix_appointments_appointment_no", "appointments", ["appointment_no"], unique=True)
    op.create_index("ix_appointments_patient_id",     "appointments", ["patient_id"])
    op.create_index("ix_appointments_doctor_id",      "appointments", ["doctor_id"])
    op.create_index("ix_appointments_scheduled_date", "appointments", ["scheduled_date"])
    op.create_index("ix_appointments_status",         "appointments", ["status"])
    op.create_index("ix_appointments_date_doctor",    "appointments", ["scheduled_date", "doctor_id"])


def downgrade() -> None:
    op.drop_table("appointments")
    op.drop_table("payments")
    op.drop_table("bill_items")
    op.drop_table("bills")
    op.drop_table("cls_result_values")
    op.drop_table("cls_results")
    op.execute("DROP TYPE IF EXISTS appointment_status")
    op.execute("DROP TYPE IF EXISTS payment_method")
    op.execute("DROP TYPE IF EXISTS bill_status")
    op.execute("DROP TYPE IF EXISTS cls_result_status")
