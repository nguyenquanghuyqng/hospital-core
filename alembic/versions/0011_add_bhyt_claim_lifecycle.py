"""add BHYT eligibility, claim, attempt, and reconciliation records"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bhyt_eligibility_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reception_id", sa.Integer(), sa.ForeignKey("receptions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("insurance_number", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("response_code", sa.String(50), nullable=True),
        sa.Column("response_payload", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("coverage_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("checked_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, cols in (("patient_id", ["patient_id"]), ("reception_id", ["reception_id"]), ("insurance_number", ["insurance_number"]), ("status", ["status"]),):
        op.create_index(f"ix_bhyt_eligibility_checks_{name}", "bhyt_eligibility_checks", cols)
    op.create_index("ix_bhyt_eligibility_checks_id", "bhyt_eligibility_checks", ["id"])

    op.create_table(
        "bhyt_claims",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), sa.ForeignKey("bills.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("examination_id", sa.Integer(), sa.ForeignKey("examinations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("claim_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("external_ref", sa.String(100), nullable=True),
        sa.Column("payload_xml", sa.Text(), nullable=True),
        sa.Column("response_payload", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("rejected_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("correction_of_id", sa.Integer(), sa.ForeignKey("bhyt_claims.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_number"),
    )
    for name, cols in (("bill_id", ["bill_id"]), ("examination_id", ["examination_id"]), ("claim_number", ["claim_number"]), ("status", ["status"]), ("external_ref", ["external_ref"]),):
        op.create_index(f"ix_bhyt_claims_{name}", "bhyt_claims", cols)
    op.create_index("ix_bhyt_claims_id", "bhyt_claims", ["id"])

    op.create_table(
        "bhyt_claim_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("bhyt_claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bill_item_id", sa.Integer(), sa.ForeignKey("bill_items.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("item_code", sa.String(50), nullable=True),
        sa.Column("item_name", sa.String(300), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("bhyt_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("accepted_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("rejected_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bhyt_claim_lines_id", "bhyt_claim_lines", ["id"])
    op.create_index("ix_bhyt_claim_lines_claim_id", "bhyt_claim_lines", ["claim_id"])

    op.create_table(
        "bhyt_claim_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("bhyt_claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_payload", sa.Text(), nullable=True),
        sa.Column("external_ref", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id", "attempt_no", name="uq_bhyt_claim_attempt"),
    )
    op.create_index("ix_bhyt_claim_attempts_id", "bhyt_claim_attempts", ["id"])
    op.create_index("ix_bhyt_claim_attempts_claim_id", "bhyt_claim_attempts", ["claim_id"])


def downgrade() -> None:
    op.drop_table("bhyt_claim_attempts")
    op.drop_table("bhyt_claim_lines")
    op.drop_table("bhyt_claims")
    op.drop_table("bhyt_eligibility_checks")
