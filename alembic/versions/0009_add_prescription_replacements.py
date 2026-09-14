"""allow replacement prescriptions while preserving successful originals"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A correction creates a new prescription for the same examination, so the
    # old one-to-one examination index must become a normal lookup index.
    op.execute("DROP INDEX IF EXISTS ix_prescriptions_examination_id")
    op.execute(
        "ALTER TABLE prescriptions "
        "DROP CONSTRAINT IF EXISTS prescriptions_examination_id_key"
    )
    op.add_column(
        "prescriptions",
        sa.Column(
            "supersedes_id",
            sa.Integer(),
            sa.ForeignKey("prescriptions.id", ondelete="SET NULL"),
            nullable=True,
            comment="Đơn cũ được thay thế khi điều chỉnh sau khi đã gửi",
        ),
    )
    op.create_index(
        "ix_prescriptions_examination_id",
        "prescriptions",
        ["examination_id"],
    )
    op.create_index(
        "ix_prescriptions_supersedes_id",
        "prescriptions",
        ["supersedes_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_prescriptions_supersedes_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_examination_id", table_name="prescriptions")
    op.drop_column("prescriptions", "supersedes_id")
    op.create_unique_constraint(
        "prescriptions_examination_id_key",
        "prescriptions",
        ["examination_id"],
    )
    op.create_index(
        "ix_prescriptions_examination_id",
        "prescriptions",
        ["examination_id"],
        unique=True,
    )