from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from sentinelops.db.base import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50), default="stripe", index=True)

    # ✅ invalid 이벤트 저장을 위해 nullable
    provider_event_id: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, index=True, nullable=True
    )
    event_type: Mapped[Optional[str]] = mapped_column(
        String(100), index=True, nullable=True
    )

    # ✅ 상태 추가 (관측 시스템의 핵심)
    status: Mapped[str] = mapped_column(String(20), default="verified", index=True)

    # ✅ 운영/디버그용 메타 (선택이지만 강추)
    signature: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    livemode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at_provider: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    raw: Mapped[dict] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
