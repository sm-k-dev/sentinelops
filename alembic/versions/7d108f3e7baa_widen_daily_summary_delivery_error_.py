"""widen_daily_summary_delivery_error_fields

Revision ID: 7d108f3e7baa
Revises: 1e5c7202c86c
Create Date: 2026-01-12 21:26:52.469918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d108f3e7baa'
down_revision: Union[str, Sequence[str], None] = '1e5c7202c86c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ✅ ai_error, slack_response를 TEXT로 확장
    op.alter_column("daily_summary_deliveries", "ai_error",
                    existing_type=sa.VARCHAR(length=100),
                    type_=sa.Text(),
                    existing_nullable=True)
    op.alter_column("daily_summary_deliveries", "slack_response",
                    existing_type=sa.VARCHAR(length=100),
                    type_=sa.Text(),
                    existing_nullable=True)

def downgrade() -> None:
    op.alter_column("daily_summary_deliveries", "slack_response",
                    existing_type=sa.Text(),
                    type_=sa.VARCHAR(length=100),
                    existing_nullable=True)
    op.alter_column("daily_summary_deliveries", "ai_error",
                    existing_type=sa.Text(),
                    type_=sa.VARCHAR(length=100),
                    existing_nullable=True)