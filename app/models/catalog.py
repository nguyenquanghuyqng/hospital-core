"""
ORM models cho danh mục hệ thống.

Bao gồm:
- Drug          — danh mục thuốc
- ClsService    — danh mục dịch vụ cận lâm sàng
- Icd10         — danh mục mã bệnh ICD-10
- SystemConfig  — cấu hình cơ sở y tế (key-value)
- AuditLog      — nhật ký thay đổi dữ liệu (ai sửa gì, khi nào)
"""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    Numeric, DateTime, func, Index,
)
from app.db.base import Base
from app.models.base_model import TimestampMixin
from app.models.enums import DrugCategory, drug_category_col


# ─── Danh mục thuốc ──────────────────────────────────────────────────────────

class Drug(Base, TimestampMixin):
    """
    Bảng ``drugs`` — danh mục thuốc của cơ sở y tế.

    Mỗi dòng là một mặt hàng thuốc với đủ thông tin để:
    - Kê đơn (tên, hoạt chất, dạng bào chế, đơn vị, liều dùng)
    - Tính viện phí (giá nhập, giá bán, tỷ lệ BHYT chi trả)
    - Kiểm soát tồn kho (stock_quantity)
    - Cảnh báo tương tác / trùng hoạt chất (active_ingredient)

    Attributes:
        drug_code: Mã thuốc nội bộ (duy nhất).
        drug_name: Tên thương mại.
        generic_name: Tên generic / INN.
        active_ingredient: Hoạt chất (dùng để cảnh báo trùng).
        drug_group: Nhóm dược lý (kháng sinh, giảm đau...).
        dosage_form: Dạng bào chế (viên, dung dịch, ống...).
        strength: Hàm lượng (VD: 500mg, 250mg/5ml).
        unit: Đơn vị tính (viên, ống, lọ...).
        unit_price: Giá bán lẻ (VND).
        bhyt_price: Giá BHYT thanh toán.
        bhyt_ratio: Tỷ lệ BHYT chi trả (0.0–1.0).
        stock_quantity: Tồn kho hiện tại.
        min_stock: Mức tồn kho tối thiểu (cảnh báo hết thuốc).
        manufacturer: Nhà sản xuất.
        country: Nước sản xuất.
        registration_no: Số đăng ký lưu hành.
        is_active: Đang sử dụng trong hệ thống.
        is_bhyt: Thuộc danh mục BHYT chi trả.
        note: Ghi chú bổ sung.
    """

    __tablename__ = "drugs"

    id             = Column(Integer, primary_key=True, index=True)
    drug_code      = Column(String(30),  unique=True, index=True, nullable=False, comment="Mã thuốc")
    drug_name      = Column(String(200), nullable=False,  comment="Tên thương mại")
    generic_name   = Column(String(200), nullable=True,   comment="Tên generic / INN")
    active_ingredient = Column(String(300), nullable=True, comment="Hoạt chất (cảnh báo trùng)")
    drug_group     = Column(String(100), nullable=True,   comment="Nhóm dược lý")
    dosage_form    = Column(String(100), nullable=True,   comment="Dạng bào chế")
    strength       = Column(String(50),  nullable=True,   comment="Hàm lượng (VD: 500mg)")
    unit           = Column(String(30),  nullable=False,  comment="Đơn vị tính (viên, ống...)")
    unit_price     = Column(Numeric(12, 0), nullable=False, server_default="0", comment="Giá bán (VND)")
    bhyt_price     = Column(Numeric(12, 0), nullable=True,  comment="Giá BHYT")
    bhyt_ratio     = Column(Numeric(4, 2),  nullable=True,  comment="Tỷ lệ BHYT chi trả (0.80 = 80%)")
    stock_quantity = Column(Integer, nullable=False, server_default="0", comment="Tồn kho")
    min_stock      = Column(Integer, nullable=False, server_default="0", comment="Tồn kho tối thiểu")
    manufacturer   = Column(String(200), nullable=True, comment="Nhà sản xuất")
    country        = Column(String(50),  nullable=True, comment="Nước sản xuất")
    registration_no = Column(String(50), nullable=True, comment="Số đăng ký lưu hành")
    is_active      = Column(Boolean, nullable=False, default=True,  server_default="true")
    is_bhyt        = Column(Boolean, nullable=False, default=False, server_default="false", comment="Thuộc DM BHYT")
    note           = Column(Text, nullable=True)

    # ── Phân loại nhóm thuốc BYT (dùng xác định ký tự Z của mã đơn) ─────────
    drug_category  = Column(
        drug_category_col,
        nullable=False,
        default=DrugCategory.REGULAR,
        server_default=DrugCategory.REGULAR.value,
        comment="regular/narcotic/psychotropic/functional_food",
    )

    __table_args__ = (
        Index("ix_drugs_drug_name", "drug_name"),
        Index("ix_drugs_active_ingredient", "active_ingredient"),
    )

    def __repr__(self) -> str:
        return f"<Drug {self.drug_code} {self.drug_name}>"


# ─── Danh mục dịch vụ CLS ────────────────────────────────────────────────────

class ClsService(Base, TimestampMixin):
    """
    Bảng ``cls_services`` — danh mục dịch vụ cận lâm sàng.

    Mỗi dòng là một loại xét nghiệm / chẩn đoán hình ảnh / thủ thuật.

    Attributes:
        service_code: Mã dịch vụ (duy nhất, theo danh mục BYT).
        service_name: Tên dịch vụ.
        service_group: Nhóm (xét nghiệm / CĐHA / thủ thuật / khác).
        unit: Đơn vị thực hiện (lần, mẫu...).
        unit_price: Giá dịch vụ.
        bhyt_price: Giá BHYT.
        bhyt_ratio: Tỷ lệ BHYT chi trả.
        result_fields: JSON schema các chỉ số kết quả (name, unit, ref_min, ref_max).
        turnaround_hours: Thời gian trả kết quả trung bình (giờ).
        department: Khoa/phòng thực hiện.
        is_active: Đang sử dụng.
        is_bhyt: Thuộc danh mục BHYT.
    """

    __tablename__ = "cls_services"

    id             = Column(Integer, primary_key=True, index=True)
    service_code   = Column(String(30),  unique=True, index=True, nullable=False, comment="Mã DV")
    service_name   = Column(String(300), nullable=False, comment="Tên dịch vụ")
    service_group  = Column(String(50),  nullable=True,  comment="Nhóm: lab/imaging/procedure/other")
    unit           = Column(String(30),  nullable=False,  server_default="'lần'", comment="Đơn vị")
    unit_price     = Column(Numeric(12, 0), nullable=False, server_default="0")
    bhyt_price     = Column(Numeric(12, 0), nullable=True)
    bhyt_ratio     = Column(Numeric(4, 2),  nullable=True,  comment="Tỷ lệ BHYT (0.80 = 80%)")
    # Lưu dạng JSON text: [{"name":"HGB","unit":"g/dL","ref_min":120,"ref_max":160}, ...]
    result_fields  = Column(Text, nullable=True, comment="JSON schema chỉ số kết quả")
    turnaround_hours = Column(Integer, nullable=True, comment="Giờ trả KQ trung bình")
    department     = Column(String(100), nullable=True, comment="Khoa/phòng thực hiện")
    is_active      = Column(Boolean, nullable=False, default=True,  server_default="true")
    is_bhyt        = Column(Boolean, nullable=False, default=False, server_default="false")
    note           = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_cls_services_service_name", "service_name"),
        Index("ix_cls_services_service_group", "service_group"),
    )

    def __repr__(self) -> str:
        return f"<ClsService {self.service_code} {self.service_name}>"


# ─── Danh mục ICD-10 ─────────────────────────────────────────────────────────

class Icd10(Base):
    """
    Bảng ``icd10`` — danh mục mã bệnh ICD-10.

    Dữ liệu import từ file BYT, chỉ đọc trong hệ thống.
    Không có TimestampMixin vì không cần audit.

    Attributes:
        code: Mã ICD-10 (VD: A00, J18.9).
        name_vi: Tên bệnh tiếng Việt.
        name_en: Tên bệnh tiếng Anh.
        chapter: Chương (VD: I, II, X...).
        block: Nhóm bệnh (VD: A00-A09).
        is_leaf: True nếu là mã cuối (có thể dùng để chẩn đoán).
    """

    __tablename__ = "icd10"

    id       = Column(Integer, primary_key=True, index=True)
    code     = Column(String(10),  unique=True, index=True, nullable=False)
    name_vi  = Column(String(500), nullable=False, comment="Tên tiếng Việt")
    name_en  = Column(String(500), nullable=True,  comment="Tên tiếng Anh")
    chapter  = Column(String(10),  nullable=True,  comment="Chương ICD")
    block    = Column(String(20),  nullable=True,  comment="Nhóm bệnh")
    is_leaf  = Column(Boolean, nullable=False, default=True, server_default="true")

    __table_args__ = (
        Index("ix_icd10_name_vi", "name_vi"),
    )

    def __repr__(self) -> str:
        return f"<Icd10 {self.code} {self.name_vi[:40]}>"


# ─── Cấu hình cơ sở ──────────────────────────────────────────────────────────

class SystemConfig(Base, TimestampMixin):
    """
    Bảng ``system_config`` — cấu hình hệ thống dạng key-value.

    Lưu các thông số cơ sở y tế và tuỳ chỉnh hệ thống.

    Các key quan trọng:
        facility_name       — Tên phòng khám/bệnh viện
        facility_code       — Mã cơ sở KCB (do BYT cấp)
        facility_address    — Địa chỉ
        facility_phone      — SĐT liên hệ
        facility_tax_code   — Mã số thuế
        bhyt_contract_no    — Số HĐ BHYT
        invoice_template    — Mẫu số hóa đơn
        default_clinic_rooms— Danh sách phòng khám mặc định (JSON)
        bhyt_copay_rate     — Tỷ lệ cùng chi trả mặc định

    Attributes:
        key: Khoá cấu hình (duy nhất).
        value: Giá trị (text, có thể là JSON).
        label: Nhãn hiển thị trên UI.
        group: Nhóm cấu hình (facility / bhyt / system / invoice).
        description: Mô tả chi tiết.
        is_public: Có thể đọc không cần admin.
        updated_by: Username admin đã cập nhật.
    """

    __tablename__ = "system_config"

    id          = Column(Integer, primary_key=True, index=True)
    key         = Column(String(100), unique=True, index=True, nullable=False)
    value       = Column(Text, nullable=True)
    label       = Column(String(200), nullable=False, comment="Nhãn UI")
    group       = Column(String(50),  nullable=False, server_default="'system'",
                         comment="facility|bhyt|system|invoice")
    description = Column(Text, nullable=True)
    is_public   = Column(Boolean, nullable=False, default=False, server_default="false")
    updated_by  = Column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<SystemConfig {self.key}={self.value!r}>"


# ─── Audit Log ───────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Bảng ``audit_logs`` — nhật ký thay đổi dữ liệu bệnh viện.

    Bắt buộc theo quy định hồ sơ y tế: mọi thay đổi trên dữ liệu lâm sàng
    phải được ghi lại để truy vết.

    Không có TimestampMixin (chỉ cần created_at, không update).
    Không bao giờ xoá dòng trong bảng này.

    Attributes:
        created_at: Thời điểm sự kiện xảy ra (UTC).
        user_id: ID người thực hiện.
        username: Username người thực hiện (snapshot, không join).
        action: Loại hành động: CREATE | UPDATE | DELETE | LOGIN | LOGOUT.
        table_name: Bảng bị tác động (VD: examinations, receptions).
        record_id: ID bản ghi bị tác động.
        old_data: Dữ liệu trước khi sửa (JSON text).
        new_data: Dữ liệu sau khi sửa (JSON text).
        ip_address: IP của client.
        description: Mô tả ngắn gọn hành động.
    """

    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, index=True)
    created_at  = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    user_id     = Column(Integer, nullable=True,  index=True, comment="ID người thực hiện")
    username    = Column(String(100), nullable=True, comment="Username snapshot")
    action      = Column(String(20),  nullable=False, index=True,
                         comment="CREATE|UPDATE|DELETE|LOGIN|LOGOUT")
    table_name  = Column(String(100), nullable=True,  index=True, comment="Bảng bị tác động")
    record_id   = Column(Integer,     nullable=True,  comment="ID bản ghi")
    old_data    = Column(Text, nullable=True, comment="JSON trước khi sửa")
    new_data    = Column(Text, nullable=True, comment="JSON sau khi sửa")
    ip_address  = Column(String(45),  nullable=True)
    description = Column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_audit_logs_table_record", "table_name", "record_id"),
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.table_name}#{self.record_id} by {self.username}>"
