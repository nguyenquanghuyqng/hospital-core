"""add updated_by audit columns to receptions and examinations

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-08 08:00:00.000000

Thêm cột audit ``updated_by`` vào hai bảng:
- ``receptions.updated_by``  — username nhân viên / bác sĩ thực hiện cập nhật cuối
- ``examinations.updated_by`` — username bác sĩ thực hiện cập nhật cuối

Mục đích:
    Đáp ứng tiêu chí audit trail: biết *ai* đã thực hiện thay đổi,
    kết hợp với ``updated_at`` từ TimestampMixin để biết *khi nào*.

Không phá vỡ dữ liệu hiện có: cột ``NULLABLE``, không có giá trị mặc định,
các bản ghi cũ sẽ có ``NULL`` là hợp lệ.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Thêm cột ``updated_by`` (VARCHAR 100, NULLABLE) vào receptions và examinations.
    """
    op.add_column(
        "receptions",
        sa.Column(
            "updated_by",
            sa.String(length=100),
            nullable=True,
            comment="Username thực hiện cập nhật cuối",
        ),
    )
    op.add_column(
        "examinations",
        sa.Column(
            "updated_by",
            sa.String(length=100),
            nullable=True,
            comment="Username thực hiện cập nhật cuối",
        ),
    )


def downgrade() -> None:
    """
    Xoá cột ``updated_by`` khỏi receptions và examinations.
    """
    op.drop_column("examinations", "updated_by")
    op.drop_column("receptions",   "updated_by")
