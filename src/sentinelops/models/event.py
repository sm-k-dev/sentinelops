from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from sentinelops.db.base import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50), default="manual", index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    raw: Mapped[str] = mapped_column(String)  # 오늘은 문자열로 단순 시작

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
