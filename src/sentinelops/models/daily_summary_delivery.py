from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import Date, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from sentinelops.db.base import Base


class DailySummaryDelivery(Base):
    """
    하루 1회 전송(idempotency)을 위한 delivery ledger.

    - kind + summary_date 유니크로 '하루 1번만' 보장
    - status:
        - pending: 실행 시작(락 역할)
        - sent: 전송 완료
        - failed: 전송 실패(원하면 다음 실행에서 재시도 가능)
        - skipped: 이미 sent였거나 정책상 스킵
    """
    __tablename__ = "daily_summary_deliveries"
    __table_args__ = (
        UniqueConstraint("kind", "summary_date", name="uq_daily_summary_kind_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    kind: Mapped[str] = mapped_column(String(50), index=True)  # 예: "daily_ops"
    summary_date: Mapped[date] = mapped_column(Date, index=True)  # window_end 기준 날짜

    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    window_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    used_ai: Mapped[Optional[bool]] = mapped_column(nullable=True)
    ai_error: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    slack_response: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
