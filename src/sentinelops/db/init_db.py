from __future__ import annotations

from sentinelops.db.session import engine
from sentinelops.db.base import Base

# 모델 import (Base에 테이블 등록되게)
from sentinelops.models import anomaly, event, daily_summary_delivery  # noqa: F401


def create_all() -> None:
    Base.metadata.create_all(bind=engine)
