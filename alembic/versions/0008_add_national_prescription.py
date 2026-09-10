"""add national prescription support

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-10 08:00:00.000000

Thay đổi:
  users             — thêm national_doctor_code, license_status
  patients          — thêm weight_kg
  drugs             — thêm drug_category
  prescriptions     — bảng mới (đơn thuốc chuẩn BYT, mã 14 ký tự)
  prescription_items — thêm prescription_id FK

Thêm PostgreSQL native ENUM types:
  license_status
  drug_category
  prescription_type
  prescription_push_status
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Enum values (hard-code để tránh import cycle khi chưa upgrade) ────────────
_LICENSE_STATUS_VALUES      = "'active', 'suspended', 'revoked'"
_DRUG_CATEGORY_VALUES       = "'regular', 'narcotic', 'psychotropic', 'functional_food'"
_PRESCRIPTION_TYPE_VALUES   = "'N', 'H', 'C'"
_PUSH_STATUS_VALUES         = "'pending', 'sending', 'success', 'error', 'cancelled'"


def upgrade() -> None:
    # ── 1. Tạo PostgreSQL native TYPEs ───────────────────────────────────────
    op.execute(f"CREATE TYPE license_status           AS ENUM ({_LICENSE_STATUS_VALUES})")
    op.execute(f"CREATE TYPE drug_category            AS ENUM ({_DRUG_CATEGORY_VALUES})")
    op.execute(f"CREATE TYPE prescription_type        AS ENUM ({_PRESCRIPTION_TYPE_VALUES})")
    op.execute(f"CREATE TYPE prescription_push_status AS ENUM ({_PUSH_STATUS_VALUES})")

    # ── 2. users — thêm mã liên thông bác sĩ ─────────────────────────────────
    op.add_column("users",
        sa.Column("national_doctor_code", sa.String(20), nullable=True,
                  comment="Mã liên thông bác sĩ (Sở Y tế cấp)"))
    op.add_column("users",
        sa.Column("license_status_str", sa.String(20), nullable=False,
                  server_default="active"))
    # 1. Drop default trước khi đổi type
    op.execute("ALTER TABLE users ALTER COLUMN license_status_str DROP DEFAULT")

    # 2. Đổi type sang enum
    op.execute(
        "ALTER TABLE users "
        "ALTER COLUMN license_status_str TYPE license_status "
        "USING license_status_str::license_status"
    )

    # 3. Set lại default, đã cast sang enum
    op.execute(
        "ALTER TABLE users "
        "ALTER COLUMN license_status_str SET DEFAULT 'active'::license_status"
    )
    op.execute("ALTER TABLE users RENAME COLUMN license_status_str TO license_status")
    op.create_index("ix_users_national_doctor_code", "users", ["national_doctor_code"])

    # ── 3. patients — thêm cân nặng ──────────────────────────────────────────
    op.add_column("patients",
        sa.Column("weight_kg", sa.Numeric(5, 1), nullable=True,
                  comment="Cân nặng (kg) — bắt buộc cho BN < 72 tháng tuổi"))

    # ── 4. drugs — thêm phân loại nhóm thuốc ─────────────────────────────────
    op.add_column("drugs",
        sa.Column("drug_category_str", sa.String(20), nullable=False,
                  server_default="regular"))
    op.execute("ALTER TABLE drugs ALTER COLUMN drug_category_str DROP DEFAULT")
    op.execute(
        "ALTER TABLE drugs "
        "ALTER COLUMN drug_category_str TYPE drug_category "
        "USING drug_category_str::drug_category"
    )
    op.execute("ALTER TABLE drugs ALTER COLUMN drug_category_str SET DEFAULT 'regular'::drug_category")
    op.execute("ALTER TABLE drugs RENAME COLUMN drug_category_str TO drug_category")
    op.create_index("ix_drugs_drug_category", "drugs", ["drug_category"])

    # ── 5. prescriptions — bảng đơn thuốc chính thức BYT ─────────────────────
    op.create_table(
        "prescriptions",
        # ── Định danh ────────────────────────────────────────────────────
        sa.Column("id",                 sa.Integer(),    nullable=False),
        sa.Column("examination_id",     sa.Integer(),
                  sa.ForeignKey("examinations.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("patient_id",         sa.Integer(),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("doctor_id",          sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True),

        # ── Mã đơn 14 ký tự: XXXXXYYYYYYY-Z ─────────────────────────────
        sa.Column("prescription_code",  sa.String(16), nullable=True,
                  comment="Mã đơn 14 ký tự: XXXXX+YYYYYYY-Z (unique per facility)"),
        sa.Column("facility_code",      sa.String(5),  nullable=True,
                  comment="5 ký tự mã cơ sở (snapshot tại thời điểm tạo)"),

        # ── Loại đơn và trạng thái đẩy ───────────────────────────────────
        sa.Column("prescription_type_str", sa.String(2), nullable=False, server_default="C"),
        sa.Column("push_status_str",       sa.String(20), nullable=False, server_default="pending"),

        # ── Timestamps gửi / bán ─────────────────────────────────────────
        sa.Column("sent_at",            sa.DateTime(timezone=True), nullable=True),
        sa.Column("sold_at",            sa.DateTime(timezone=True), nullable=True),
        sa.Column("national_ref_id",    sa.String(100), nullable=True,
                  comment="ID đơn trên hệ thống quốc gia (response từ BYT)"),

        # ── Hình thức điều trị ────────────────────────────────────────────
        sa.Column("is_inpatient",       sa.Boolean(), nullable=False, server_default="false",
                  comment="True=Nội trú, False=Ngoại trú"),

        # ── Đợt dùng thuốc (bắt buộc với N/H) ────────────────────────────
        sa.Column("treatment_from",     sa.Date(), nullable=True,
                  comment="Đợt dùng thuốc từ ngày (bắt buộc với N/H)"),
        sa.Column("treatment_to",       sa.Date(), nullable=True,
                  comment="Đợt dùng thuốc đến ngày (bắt buộc với N/H)"),

        # ── Thông tin BN snapshot tại thời điểm kê ────────────────────────
        sa.Column("patient_phone",      sa.String(20),  nullable=True,
                  comment="SĐT bệnh nhân (bắt buộc trên mọi đơn)"),
        sa.Column("patient_weight_kg",  sa.Numeric(5, 1), nullable=True,
                  comment="Cân nặng snapshot (bắt buộc BN < 72 tháng)"),
        sa.Column("patient_gender_code",sa.SmallInteger(), nullable=True,
                  comment="Giới tính mã hóa BYT: 1=Nam, 2=Nữ, 3=Khác"),
        sa.Column("guardian_name",      sa.String(100), nullable=True,
                  comment="Tên bố/mẹ/người đưa trẻ — bắt buộc BN < 72 tháng"),

        # ── Người nhận (đặc biệt đơn N/H) ────────────────────────────────
        sa.Column("recipient_cccd",     sa.String(12), nullable=True,
                  comment="CCCD/CMND người nhận thuốc N/H"),
        sa.Column("recipient_name",     sa.String(100), nullable=True,
                  comment="Họ tên người nhận thuốc N/H"),

        # ── Retry và log lỗi ──────────────────────────────────────────────
        sa.Column("retry_count",        sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_at",           sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_log",          sa.Text(), nullable=True,
                  comment="Log lỗi gửi API BYT (JSON)"),

        # ── Snapshot bác sĩ ───────────────────────────────────────────────
        sa.Column("doctor_name",        sa.String(100), nullable=True),
        sa.Column("doctor_national_code", sa.String(20), nullable=True,
                  comment="Mã liên thông BS snapshot tại thời điểm kê"),

        # ── Timestamps ───────────────────────────────────────────────────
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),

        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prescription_code", name="uq_prescriptions_code"),
    )

    # Chuyển sang native enum
    op.execute("ALTER TABLE prescriptions ALTER COLUMN prescription_type_str DROP DEFAULT")
    op.execute(
        "ALTER TABLE prescriptions "
        "ALTER COLUMN prescription_type_str TYPE prescription_type "
        "USING prescription_type_str::prescription_type"
    )
    op.execute("ALTER TABLE prescriptions ALTER COLUMN prescription_type_str SET DEFAULT 'C'::prescription_type")
    op.execute("ALTER TABLE prescriptions RENAME COLUMN prescription_type_str TO prescription_type")

    op.execute("ALTER TABLE prescriptions ALTER COLUMN push_status_str DROP DEFAULT")
    op.execute(
        "ALTER TABLE prescriptions "
        "ALTER COLUMN push_status_str TYPE prescription_push_status "
        "USING push_status_str::prescription_push_status"
    )
    op.execute("ALTER TABLE prescriptions ALTER COLUMN push_status_str SET DEFAULT 'pending'::prescription_push_status")
    op.execute("ALTER TABLE prescriptions RENAME COLUMN push_status_str TO push_status")

    # Indexes
    op.create_index("ix_prescriptions_id",             "prescriptions", ["id"])
    op.create_index("ix_prescriptions_examination_id", "prescriptions", ["examination_id"], unique=True)
    op.create_index("ix_prescriptions_patient_id",     "prescriptions", ["patient_id"])
    op.create_index("ix_prescriptions_doctor_id",      "prescriptions", ["doctor_id"])
    op.create_index("ix_prescriptions_push_status",    "prescriptions", ["push_status"])
    op.create_index("ix_prescriptions_prescription_type", "prescriptions", ["prescription_type"])

    # ── 6. prescription_items — thêm FK tới prescriptions ────────────────────
    op.add_column("prescription_items",
        sa.Column("prescription_id", sa.Integer(),
                  sa.ForeignKey("prescriptions.id", ondelete="SET NULL"),
                  nullable=True,
                  comment="FK tới prescriptions — gán khi tạo/đóng đơn"))
    op.create_index("ix_prescription_items_prescription_id",
                    "prescription_items", ["prescription_id"])


def downgrade() -> None:
    # ── Đảo ngược theo thứ tự ngược lại ──────────────────────────────────────
    op.drop_index("ix_prescription_items_prescription_id", "prescription_items")
    op.drop_column("prescription_items", "prescription_id")

    op.drop_index("ix_prescriptions_prescription_type",  "prescriptions")
    op.drop_index("ix_prescriptions_push_status",        "prescriptions")
    op.drop_index("ix_prescriptions_doctor_id",          "prescriptions")
    op.drop_index("ix_prescriptions_patient_id",         "prescriptions")
    op.drop_index("ix_prescriptions_examination_id",     "prescriptions")
    op.drop_index("ix_prescriptions_id",                 "prescriptions")
    op.drop_table("prescriptions")

    op.drop_index("ix_drugs_drug_category", "drugs")
    op.execute("ALTER TABLE drugs RENAME COLUMN drug_category TO drug_category_str")
    op.execute("ALTER TABLE drugs ALTER COLUMN drug_category_str TYPE VARCHAR(20) USING drug_category_str::text")
    op.drop_column("drugs", "drug_category_str")

    op.drop_column("patients", "weight_kg")

    op.drop_index("ix_users_national_doctor_code", "users")
    op.execute("ALTER TABLE users RENAME COLUMN license_status TO license_status_str")
    # 1. Drop the existing default
    op.execute("ALTER TABLE users ALTER COLUMN license_status_str DROP DEFAULT")

    # 2. Change the column type, casting existing data via ::text -> ::license_status
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN license_status_str TYPE license_status
        USING license_status_str::text::license_status
    """)

    # 3. Re-add the default, now cast to the enum type
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN license_status_str SET DEFAULT 'active'::license_status
    """)
    op.drop_column("users", "national_doctor_code")

    op.execute("DROP TYPE prescription_push_status")
    op.execute("DROP TYPE prescription_type")
    op.execute("DROP TYPE drug_category")
    op.execute("DROP TYPE license_status")
