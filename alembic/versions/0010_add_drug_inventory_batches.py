"""add batch-aware drug inventory and immutable stock ledger"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "drug_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("drug_id", sa.Integer(), sa.ForeignKey("drugs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lot_number", sa.String(100), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("received_quantity", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("available_quantity", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("supplier", sa.String(200), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("active", sa.String(1), nullable=False, server_default="Y"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drug_id", "lot_number", "expiry_date", name="uq_drug_batches_drug_lot_expiry"),
    )
    op.create_index("ix_drug_batches_id", "drug_batches", ["id"])
    op.create_index("ix_drug_batches_drug_id", "drug_batches", ["drug_id"])
    op.create_index("ix_drug_batches_expiry_date", "drug_batches", ["expiry_date"])
    op.create_index("ix_drug_batches_available_expiry", "drug_batches", ["drug_id", "available_quantity", "expiry_date"])

    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("drug_id", sa.Integer(), sa.ForeignKey("drugs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("drug_batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 2), nullable=False),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_transactions_id", "inventory_transactions", ["id"])
    op.create_index("ix_inventory_transactions_drug_id", "inventory_transactions", ["drug_id"])
    op.create_index("ix_inventory_transactions_batch_id", "inventory_transactions", ["batch_id"])
    op.create_index("ix_inventory_transactions_transaction_type", "inventory_transactions", ["transaction_type"])
    op.create_index("ix_inventory_transactions_actor_id", "inventory_transactions", ["actor_id"])
    op.create_index("ix_inventory_transactions_created_at", "inventory_transactions", ["created_at"])
    op.create_index("ix_inventory_transactions_source", "inventory_transactions", ["source_type", "source_id"])


def downgrade() -> None:
    op.drop_table("inventory_transactions")
    op.drop_table("drug_batches")
