"""add anomalies table

Revision ID: 214644219862
Revises: 46ee09cd231d
Create Date: 2026-01-09 16:55:14.196077
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "214644219862"
down_revision: Union[str, Sequence[str], None] = "46ee09cd231d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Table
    op.create_table(
        "anomalies",
        sa.Column("id", sa.Integer(), primary_key=True),

        sa.Column("rule_code", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),

        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),

        sa.Column("event_type", sa.String(length=100), nullable=True),
        sa.Column("provider_event_id", sa.String(length=100), nullable=True),

        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),

        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    # 2) Indexes
    op.create_index("ix_anomalies_rule_code", "anomalies", ["rule_code"])
    op.create_index("ix_anomalies_severity", "anomalies", ["severity"])
    op.create_index("ix_anomalies_status", "anomalies", ["status"])
    op.create_index("ix_anomalies_event_type", "anomalies", ["event_type"])
    op.create_index("ix_anomalies_provider_event_id", "anomalies", ["provider_event_id"])
    op.create_index("ix_anomalies_detected_at", "anomalies", ["detected_at"])


def downgrade() -> None:
    # DB에 실제로 생성된 적이 없을 수 있으니, 존재할 때만 drop
    for ix in [
        "ix_anomalies_detected_at",
        "ix_anomalies_provider_event_id",
        "ix_anomalies_event_type",
        "ix_anomalies_status",
        "ix_anomalies_severity",
        "ix_anomalies_rule_code",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {ix};")

    op.execute("DROP TABLE IF EXISTS anomalies;")

