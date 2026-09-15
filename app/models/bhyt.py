"""BHYT eligibility, claim submission, and reconciliation records."""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func

from app.db.base import Base


class BhytEligibilityCheck(Base):
    __tablename__ = "bhyt_eligibility_checks"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    reception_id = Column(Integer, ForeignKey("receptions.id", ondelete="SET NULL"), nullable=True, index=True)
    insurance_number = Column(String(20), nullable=False, index=True)
    status = Column(String(30), nullable=False, index=True)
    response_code = Column(String(50), nullable=True)
    response_payload = Column(Text, nullable=True)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    coverage_percent = Column(Numeric(5, 2), nullable=True)
    checked_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    checked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BhytClaim(Base):
    __tablename__ = "bhyt_claims"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id", ondelete="RESTRICT"), nullable=False, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="RESTRICT"), nullable=False, index=True)
    claim_number = Column(String(50), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, server_default="draft", index=True)
    external_ref = Column(String(100), nullable=True, index=True)
    payload_xml = Column(Text, nullable=True)
    response_payload = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_amount = Column(Numeric(15, 2), nullable=True)
    rejected_amount = Column(Numeric(15, 2), nullable=True)
    correction_of_id = Column(Integer, ForeignKey("bhyt_claims.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BhytClaimLine(Base):
    __tablename__ = "bhyt_claim_lines"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("bhyt_claims.id", ondelete="CASCADE"), nullable=False, index=True)
    bill_item_id = Column(Integer, ForeignKey("bill_items.id", ondelete="RESTRICT"), nullable=True)
    item_code = Column(String(50), nullable=True)
    item_name = Column(String(300), nullable=False)
    quantity = Column(Numeric(14, 2), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    bhyt_amount = Column(Numeric(15, 2), nullable=False)
    accepted_amount = Column(Numeric(15, 2), nullable=True)
    rejected_amount = Column(Numeric(15, 2), nullable=True)
    rejection_reason = Column(Text, nullable=True)


class BhytClaimAttempt(Base):
    __tablename__ = "bhyt_claim_attempts"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("bhyt_claims.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_no = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_payload = Column(Text, nullable=True)
    external_ref = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("uq_bhyt_claim_attempt", "claim_id", "attempt_no", unique=True),
    )
