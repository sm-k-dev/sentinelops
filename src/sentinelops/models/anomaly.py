from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sentinelops.db.base import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(primary_key=True)

    rule_code: Mapped[str] = mapped_column(String(50), index=True)
    # v0.2에서는 severity/status를 string으로 두자. (단순 + 빠름)
    severity: Mapped[str] = mapped_column(String(10), index=True)

    title: Mapped[str] = mapped_column(String(200))
    # v0.2에서는 severity/status를 string으로 두자. (단순 + 빠름)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)

    event_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    provider_event_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    window_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)

    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
