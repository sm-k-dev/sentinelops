from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1e5c7202c86c"
down_revision = "214644219862"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_summary_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("summary_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),

        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),

        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column("used_ai", sa.Boolean(), nullable=True),
        sa.Column("ai_error", sa.String(length=100), nullable=True),
        sa.Column("slack_response", sa.String(length=200), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("kind", "summary_date", name="uq_daily_summary_kind_date"),
    )

    op.create_index("ix_daily_summary_deliveries_kind", "daily_summary_deliveries", ["kind"])
    op.create_index("ix_daily_summary_deliveries_summary_date", "daily_summary_deliveries", ["summary_date"])
    op.create_index("ix_daily_summary_deliveries_status", "daily_summary_deliveries", ["status"])


def downgrade() -> None:
    op.drop_index("ix_daily_summary_deliveries_status", table_name="daily_summary_deliveries")
    op.drop_index("ix_daily_summary_deliveries_summary_date", table_name="daily_summary_deliveries")
    op.drop_index("ix_daily_summary_deliveries_kind", table_name="daily_summary_deliveries")
    op.drop_table("daily_summary_deliveries")
