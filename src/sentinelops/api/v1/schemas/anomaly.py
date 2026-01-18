from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AnomalyStatusUpdateIn(BaseModel):
    status: str


class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_code: str
    severity: str
    title: str
    status: str
    event_type: Optional[str] = None
    provider_event_id: Optional[str] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    detected_at: datetime
    evidence: dict[str, Any]
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    updated_at: datetime


class AnomalyListOut(BaseModel):
    items: list[AnomalyOut]
    count: int
