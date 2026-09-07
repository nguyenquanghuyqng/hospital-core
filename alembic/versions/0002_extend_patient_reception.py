"""extend patient and reception with full Vietnamese hospital fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-07 08:00:00.000000

Thêm các trường mới vào bảng patients và receptions theo chuẩn
form đăng ký tiếp đón bệnh nhân tại bệnh viện Việt Nam.
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────
    # patients — thêm các trường hành chính đầy đủ
    # ──────────────────────────────────────────────────────────────────
    op.add_column("patients", sa.Column(
        "patient_code", sa.String(20), nullable=True,
        comment="Mã BN (tự sinh, VD: BN20260001)"
    ))
    op.create_index("ix_patients_patient_code", "patients", ["patient_code"], unique=True)

    op.add_column("patients", sa.Column("birth_year",    sa.Integer(),     nullable=True, comment="Năm sinh"))
    op.add_column("patients", sa.Column("cccd_issued_by",   sa.String(200), nullable=True, comment="Nơi cấp CCCD/CMND"))
    op.add_column("patients", sa.Column("cccd_issued_date", sa.Date(),      nullable=True, comment="Ngày cấp CCCD/CMND"))
    op.add_column("patients", sa.Column("occupation",       sa.String(100), nullable=True, comment="Nghề nghiệp"))

    # Dân tộc
    op.add_column("patients", sa.Column("ethnicity_code", sa.String(10),  nullable=True, comment="Mã dân tộc (VD: 25)"))
    op.add_column("patients", sa.Column("ethnicity_name", sa.String(50),  nullable=True, comment="Tên dân tộc (VD: Kinh)"))

    # Quốc tịch
    op.add_column("patients", sa.Column("nationality_code", sa.String(10),  nullable=True, comment="Mã quốc tịch (VD: VN)"))
    op.add_column("patients", sa.Column("nationality_name", sa.String(100), nullable=True, comment="Tên quốc tịch (VD: VIET NAM)"))

    # Địa chỉ chi tiết
    op.add_column("patients", sa.Column("address_street",        sa.String(200), nullable=True, comment="Số nhà, đường"))
    op.add_column("patients", sa.Column("address_village",       sa.String(100), nullable=True, comment="Thôn/phố"))
    op.add_column("patients", sa.Column("address_ward_code",     sa.String(10),  nullable=True, comment="Mã phường/xã"))
    op.add_column("patients", sa.Column("address_ward_name",     sa.String(100), nullable=True, comment="Tên phường/xã"))
    op.add_column("patients", sa.Column("address_district_code", sa.String(10),  nullable=True, comment="Mã quận/huyện"))
    op.add_column("patients", sa.Column("address_district_name", sa.String(100), nullable=True, comment="Tên quận/huyện"))
    op.add_column("patients", sa.Column("address_province_code", sa.String(10),  nullable=True, comment="Mã tỉnh/TP (VD: 505)"))
    op.add_column("patients", sa.Column("address_province_name", sa.String(100), nullable=True, comment="Tên tỉnh/TP"))

    # Nơi làm việc
    op.add_column("patients", sa.Column("workplace", sa.String(200), nullable=True, comment="Nơi làm việc"))

    # Đối tượng chính sách
    op.add_column("patients", sa.Column("policy_type", sa.String(50), nullable=True, comment="Loại đối tượng chính sách"))

    # Người thân
    op.add_column("patients", sa.Column("contact_name",    sa.String(100), nullable=True, comment="Họ tên người thân"))
    op.add_column("patients", sa.Column("contact_address", sa.String(200), nullable=True, comment="Địa chỉ người thân"))
    op.add_column("patients", sa.Column("contact_phone",   sa.String(15),  nullable=True, comment="SĐT người thân"))
    op.add_column("patients", sa.Column("contact_cccd",    sa.String(12),  nullable=True, comment="CMND người thân"))

    # ──────────────────────────────────────────────────────────────────
    # receptions — thêm các trường đăng ký khám đầy đủ
    # ──────────────────────────────────────────────────────────────────
    op.add_column("receptions", sa.Column("visit_time",   sa.String(8),  nullable=True, comment="Giờ đăng ký (HH:MM)"))
    op.add_column("receptions", sa.Column("clinic_room",  sa.String(50), nullable=True, comment="Phòng khám"))
    op.add_column("receptions", sa.Column("visit_number", sa.Integer(),  nullable=True, comment="Số khám"))

    # Cờ loại đăng ký
    op.add_column("receptions", sa.Column(
        "is_appointment", sa.Boolean(), nullable=False,
        server_default=sa.text("false"), comment="Hẹn khám"
    ))
    op.add_column("receptions", sa.Column(
        "is_online", sa.Boolean(), nullable=False,
        server_default=sa.text("false"), comment="Đăng ký online"
    ))
    op.add_column("receptions", sa.Column(
        "is_referral", sa.Boolean(), nullable=False,
        server_default=sa.text("false"), comment="Chuyển tuyến"
    ))

    # Đối tượng BHYT
    op.add_column("receptions", sa.Column("subject_type", sa.String(10),  nullable=True, comment="Mã đối tượng (1=BHYT, 2=DV...)"))
    op.add_column("receptions", sa.Column("subject_name", sa.String(100), nullable=True, comment="Tên đối tượng"))

    # BHYT chi tiết
    op.add_column("receptions", sa.Column("insurance_valid_from", sa.Date(), nullable=True, comment="Từ ngày hạn thẻ BHYT"))
    op.add_column("receptions", sa.Column("insurance_valid_to",   sa.Date(), nullable=True, comment="Đến ngày hạn thẻ BHYT"))

    # ĐKKCB và giới thiệu
    op.add_column("receptions", sa.Column("initial_registration", sa.String(200), nullable=True, comment="ĐKKCB — nơi KCB ban đầu"))
    op.add_column("receptions", sa.Column("referral_note",        sa.Text(),      nullable=True, comment="Giới thiệu"))
    op.add_column("receptions", sa.Column("referral_facility",    sa.String(200), nullable=True, comment="Cơ sở giới thiệu/chuyển tuyến"))

    # Quyền lợi đặc biệt
    op.add_column("receptions", sa.Column(
        "high_tech_service", sa.Boolean(), nullable=False,
        server_default=sa.text("false"), comment="Được hưởng DVKT cao"
    ))
    op.add_column("receptions", sa.Column(
        "insurance_5years", sa.Boolean(), nullable=False,
        server_default=sa.text("false"), comment="BHYT > 5 năm"
    ))
    op.add_column("receptions", sa.Column("insurance_5years_date", sa.Date(), nullable=True, comment="Ngày tính BHYT > 5 năm"))

    # Trạng thái đặc biệt & nghèo
    op.add_column("receptions", sa.Column("special_status", sa.String(100), nullable=True, comment="Trạng thái đặc biệt"))
    op.add_column("receptions", sa.Column(
        "is_near_poor", sa.Boolean(), nullable=False,
        server_default=sa.text("false"), comment="Hộ cận nghèo"
    ))
    op.add_column("receptions", sa.Column(
        "is_poor", sa.Boolean(), nullable=False,
        server_default=sa.text("false"), comment="Hộ nghèo"
    ))

    # Phân loại bệnh nhân
    op.add_column("receptions", sa.Column("patient_category", sa.String(50), nullable=True, comment="Người lớn / Trẻ em"))
    op.add_column("receptions", sa.Column("patient_type",     sa.String(10), nullable=True, comment="Mới / Cũ"))


def downgrade() -> None:
    # ── receptions ──
    for col in [
        "patient_type", "patient_category",
        "is_poor", "is_near_poor", "special_status",
        "insurance_5years_date", "insurance_5years", "high_tech_service",
        "referral_facility", "referral_note", "initial_registration",
        "insurance_valid_to", "insurance_valid_from",
        "subject_name", "subject_type",
        "is_referral", "is_online", "is_appointment",
        "visit_number", "clinic_room", "visit_time",
    ]:
        op.drop_column("receptions", col)

    # ── patients ──
    op.drop_index("ix_patients_patient_code", table_name="patients")
    for col in [
        "contact_cccd", "contact_phone", "contact_address", "contact_name",
        "policy_type", "workplace",
        "address_province_name", "address_province_code",
        "address_district_name", "address_district_code",
        "address_ward_name", "address_ward_code",
        "address_village", "address_street",
        "nationality_name", "nationality_code",
        "ethnicity_name", "ethnicity_code",
        "occupation",
        "cccd_issued_date", "cccd_issued_by",
        "birth_year", "patient_code",
    ]:
        op.drop_column("patients", col)
