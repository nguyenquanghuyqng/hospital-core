"""
Model bệnh nhân — lưu đầy đủ thông tin hành chính theo chuẩn bệnh viện Việt Nam.
"""
from sqlalchemy import Column, Integer, String, Date, Text, Boolean
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.base_model import TimestampMixin


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)

    # ── I. HÀNH CHÍNH ──────────────────────────────────────────────────

    # Mã bệnh nhân (tự sinh, VD: BN20260001)
    patient_code = Column(String(20), unique=True, index=True, nullable=True, comment="Mã BN")

    # Thông tin cá nhân
    full_name     = Column(String(100), nullable=False, comment="Họ và tên")
    date_of_birth = Column(Date, nullable=True, comment="Ngày sinh")
    birth_year    = Column(Integer, nullable=True, comment="Năm sinh")
    gender        = Column(String(10), nullable=True, comment="Giới tính: male / female")

    # CCCD / CMND
    cccd            = Column(String(12), unique=True, index=True, nullable=True, comment="Số CCCD/CMND")
    cccd_issued_by  = Column(String(200), nullable=True, comment="Nơi cấp CCCD/CMND")
    cccd_issued_date = Column(Date, nullable=True, comment="Ngày cấp CCCD/CMND")

    # Nghề nghiệp, dân tộc, quốc tịch
    occupation      = Column(String(100), nullable=True, comment="Nghề nghiệp")
    ethnicity_code  = Column(String(10), nullable=True, comment="Mã dân tộc (VD: 25)")
    ethnicity_name  = Column(String(50), nullable=True, comment="Tên dân tộc (VD: Kinh)")
    nationality_code = Column(String(10), nullable=True, comment="Mã quốc tịch (VD: VN)")
    nationality_name = Column(String(100), nullable=True, comment="Tên quốc tịch (VD: VIET NAM)")

    # Địa chỉ chi tiết
    address_street   = Column(String(200), nullable=True, comment="Số nhà, đường")
    address_village  = Column(String(100), nullable=True, comment="Thôn/phố")
    address_ward_code = Column(String(10), nullable=True, comment="Mã phường/xã")
    address_ward_name = Column(String(100), nullable=True, comment="Tên phường/xã")
    address_district_code = Column(String(10), nullable=True, comment="Mã quận/huyện")
    address_district_name = Column(String(100), nullable=True, comment="Tên quận/huyện")
    address_province_code = Column(String(10), nullable=True, comment="Mã tỉnh/TP (VD: 505)")
    address_province_name = Column(String(100), nullable=True, comment="Tên tỉnh/TP (VD: Tỉnh Quảng Ngãi)")
    address          = Column(Text, nullable=True, comment="Địa chỉ đầy đủ (để tương thích ngược)")

    # Nơi làm việc
    workplace = Column(String(200), nullable=True, comment="Nơi làm việc")

    # Liên hệ
    phone = Column(String(15), nullable=True, comment="Số điện thoại di động")
    email = Column(String(100), nullable=True, comment="Email")

    # Đối tượng chính sách (hộ nghèo, cận nghèo...)
    policy_type = Column(String(50), nullable=True, comment="Loại đối tượng chính sách")

    # Thông tin người thân / người đi cùng
    contact_name    = Column(String(100), nullable=True, comment="Họ tên người thân")
    contact_address = Column(String(200), nullable=True, comment="Địa chỉ người thân")
    contact_phone   = Column(String(15), nullable=True, comment="SĐT người thân")
    contact_cccd    = Column(String(12), nullable=True, comment="CMND người thân")

    # ── Quan hệ ────────────────────────────────────────────────────────
    queue_tickets = relationship("QueueTicket", back_populates="patient", lazy="select")
    receptions    = relationship("Reception",   back_populates="patient", lazy="select")

    def __repr__(self) -> str:
        return f"<Patient id={self.id} code={self.patient_code} name={self.full_name}>"
