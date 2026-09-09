"""add catalog tables and audit log

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-09 10:00:00.000000

Tạo 5 bảng mới cho nền tảng hệ thống:
  - drugs         — danh mục thuốc
  - cls_services  — danh mục dịch vụ cận lâm sàng
  - icd10         — danh mục mã bệnh ICD-10
  - system_config — cấu hình cơ sở y tế
  - audit_logs    — nhật ký thay đổi dữ liệu (bắt buộc cho hồ sơ y tế)

Không phá vỡ dữ liệu hiện có.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ── drugs ─────────────────────────────────────────────────────────────────
    op.create_table(
        "drugs",
        sa.Column("id",               sa.Integer(),     nullable=False),
        sa.Column("drug_code",        sa.String(30),    nullable=False, comment="Mã thuốc"),
        sa.Column("drug_name",        sa.String(200),   nullable=False, comment="Tên thương mại"),
        sa.Column("generic_name",     sa.String(200),   nullable=True,  comment="Tên generic / INN"),
        sa.Column("active_ingredient",sa.String(300),   nullable=True,  comment="Hoạt chất"),
        sa.Column("drug_group",       sa.String(100),   nullable=True,  comment="Nhóm dược lý"),
        sa.Column("dosage_form",      sa.String(100),   nullable=True,  comment="Dạng bào chế"),
        sa.Column("strength",         sa.String(50),    nullable=True,  comment="Hàm lượng"),
        sa.Column("unit",             sa.String(30),    nullable=False, comment="Đơn vị tính"),
        sa.Column("unit_price",       sa.Numeric(12, 0),nullable=False, server_default="0"),
        sa.Column("bhyt_price",       sa.Numeric(12, 0),nullable=True),
        sa.Column("bhyt_ratio",       sa.Numeric(4, 2), nullable=True),
        sa.Column("stock_quantity",   sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("min_stock",        sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("manufacturer",     sa.String(200),   nullable=True),
        sa.Column("country",          sa.String(50),    nullable=True),
        sa.Column("registration_no",  sa.String(50),    nullable=True,  comment="Số ĐK lưu hành"),
        sa.Column("is_active",        sa.Boolean(),     nullable=False, server_default="true"),
        sa.Column("is_bhyt",          sa.Boolean(),     nullable=False, server_default="false"),
        sa.Column("note",             sa.Text(),        nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_drugs_id"),               "drugs", ["id"])
    op.create_index(op.f("ix_drugs_drug_code"),        "drugs", ["drug_code"],        unique=True)
    op.create_index(op.f("ix_drugs_drug_name"),        "drugs", ["drug_name"])
    op.create_index(op.f("ix_drugs_active_ingredient"),"drugs", ["active_ingredient"])

    # ── cls_services ──────────────────────────────────────────────────────────
    op.create_table(
        "cls_services",
        sa.Column("id",               sa.Integer(),     nullable=False),
        sa.Column("service_code",     sa.String(30),    nullable=False, comment="Mã DV"),
        sa.Column("service_name",     sa.String(300),   nullable=False, comment="Tên dịch vụ"),
        sa.Column("service_group",    sa.String(50),    nullable=True,  comment="lab/imaging/procedure/other"),
        sa.Column("unit",             sa.String(30),    nullable=False, server_default="'lần'"),
        sa.Column("unit_price",       sa.Numeric(12, 0),nullable=False, server_default="0"),
        sa.Column("bhyt_price",       sa.Numeric(12, 0),nullable=True),
        sa.Column("bhyt_ratio",       sa.Numeric(4, 2), nullable=True),
        sa.Column("result_fields",    sa.Text(),        nullable=True,  comment="JSON schema chỉ số kết quả"),
        sa.Column("turnaround_hours", sa.Integer(),     nullable=True,  comment="Giờ trả KQ TB"),
        sa.Column("department",       sa.String(100),   nullable=True,  comment="Khoa thực hiện"),
        sa.Column("is_active",        sa.Boolean(),     nullable=False, server_default="true"),
        sa.Column("is_bhyt",          sa.Boolean(),     nullable=False, server_default="false"),
        sa.Column("note",             sa.Text(),        nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cls_services_id"),           "cls_services", ["id"])
    op.create_index(op.f("ix_cls_services_service_code"), "cls_services", ["service_code"], unique=True)
    op.create_index(op.f("ix_cls_services_service_name"), "cls_services", ["service_name"])
    op.create_index(op.f("ix_cls_services_service_group"),"cls_services", ["service_group"])

    # ── icd10 ─────────────────────────────────────────────────────────────────
    op.create_table(
        "icd10",
        sa.Column("id",      sa.Integer(),    nullable=False),
        sa.Column("code",    sa.String(10),   nullable=False),
        sa.Column("name_vi", sa.String(500),  nullable=False, comment="Tên tiếng Việt"),
        sa.Column("name_en", sa.String(500),  nullable=True,  comment="Tên tiếng Anh"),
        sa.Column("chapter", sa.String(10),   nullable=True),
        sa.Column("block",   sa.String(20),   nullable=True),
        sa.Column("is_leaf", sa.Boolean(),    nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_icd10_id"),      "icd10", ["id"])
    op.create_index(op.f("ix_icd10_code"),    "icd10", ["code"],    unique=True)
    op.create_index(op.f("ix_icd10_name_vi"), "icd10", ["name_vi"])

    # ── system_config ─────────────────────────────────────────────────────────
    op.create_table(
        "system_config",
        sa.Column("id",          sa.Integer(),    nullable=False),
        sa.Column("key",         sa.String(100),  nullable=False),
        sa.Column("value",       sa.Text(),       nullable=True),
        sa.Column("label",       sa.String(200),  nullable=False, comment="Nhãn UI"),
        sa.Column("group",       sa.String(50),   nullable=False, server_default="'system'"),
        sa.Column("description", sa.Text(),       nullable=True),
        sa.Column("is_public",   sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("updated_by",  sa.String(100),  nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_system_config_id"),  "system_config", ["id"])
    op.create_index(op.f("ix_system_config_key"), "system_config", ["key"], unique=True)

    # Seed cấu hình cơ sở mặc định
    op.execute("""
        INSERT INTO system_config (key, value, label, "group", description, is_public) VALUES
        ('facility_name',      'Phòng Khám Đa Khoa',  'Tên cơ sở y tế',          'facility', 'Tên hiển thị trên phiếu khám và hóa đơn', true),
        ('facility_code',      '',                    'Mã cơ sở KCB',             'facility', 'Mã do Bộ Y tế cấp', false),
        ('facility_address',   '',                    'Địa chỉ',                  'facility', NULL, true),
        ('facility_phone',     '',                    'Số điện thoại',             'facility', NULL, true),
        ('facility_tax_code',  '',                    'Mã số thuế',               'facility', NULL, false),
        ('bhyt_contract_no',   '',                    'Số hợp đồng BHYT',         'bhyt',     NULL, false),
        ('bhyt_copay_rate',    '0.20',                'Tỷ lệ cùng chi trả mặc định','bhyt',   '20% cùng chi trả', false),
        ('invoice_template',   '01/GTGT',             'Mẫu số hóa đơn',           'invoice',  NULL, false),
        ('default_clinic_rooms','["Phòng 1","Phòng 2","Phòng 3","Phòng 4"]', 'Danh sách phòng khám', 'system', 'JSON array', false),
        ('app_version',        '1.0.0',               'Phiên bản phần mềm',       'system',   NULL, true)
    """)

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id",          sa.Integer(),             nullable=False),
        sa.Column("created_at",  sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id",     sa.Integer(),             nullable=True),
        sa.Column("username",    sa.String(100),           nullable=True),
        sa.Column("action",      sa.String(20),            nullable=False),
        sa.Column("table_name",  sa.String(100),           nullable=True),
        sa.Column("record_id",   sa.Integer(),             nullable=True),
        sa.Column("old_data",    sa.Text(),                nullable=True),
        sa.Column("new_data",    sa.Text(),                nullable=True),
        sa.Column("ip_address",  sa.String(45),            nullable=True),
        sa.Column("description", sa.String(500),           nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("idx_audit_logs_id"),           "audit_logs", ["id"])
    op.create_index(op.f("idx_audit_logs_created_at"),   "audit_logs", ["created_at"])
    op.create_index(op.f("idx_audit_logs_user_id"),      "audit_logs", ["user_id"])
    op.create_index(op.f("idx_audit_logs_action"),       "audit_logs", ["action"])
    op.create_index(op.f("idx_audit_logs_table_name"),   "audit_logs", ["table_name"])
    op.create_index("idx_audit_logs_table_record",       "audit_logs", ["table_name", "record_id"])
    op.create_index("idx_audit_logs_user_created",       "audit_logs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("system_config")
    op.drop_table("icd10")
    op.drop_table("cls_services")
    op.drop_table("drugs")
