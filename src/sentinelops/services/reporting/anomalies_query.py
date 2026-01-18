from __future__ import annotations

from sqlalchemy import case, desc, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from typing import cast

from sentinelops.models.anomaly import Anomaly


def severity_rank_expr():
    # high > medium > low (모르는 값은 맨 아래)
    return case(
        (Anomaly.severity == "high", 3),
        (Anomaly.severity == "medium", 2),
        (Anomaly.severity == "low", 1),
        else_=0,
    )


def list_anomalies(
    db: Session,
    status: str | None = None,
    only_open: bool = False,
    sort: str = "recent",
    limit: int = 50,
    demo_only: bool = False,
) -> list[Anomaly]:
    stmt = select(Anomaly)

    if only_open:
        stmt = stmt.where(Anomaly.status == "open")
    elif status:
        stmt = stmt.where(Anomaly.status == status)
    
    if demo_only:
        stmt = stmt.where(
            Anomaly.evidence["._demo"].as_boolean() == True  # noqa: E712
        )

    if sort == "severity_desc":
        stmt = stmt.order_by(desc(severity_rank_expr()), desc(Anomaly.detected_at))
    else:
        # recent
        stmt = stmt.order_by(desc(Anomaly.detected_at))

    stmt = stmt.limit(limit)
    return cast(list[Anomaly], db.execute(stmt).scalars().all())
