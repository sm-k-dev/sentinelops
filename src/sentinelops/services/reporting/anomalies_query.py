from __future__ import annotations

from typing import cast

from sqlalchemy import case, desc, select, or_
from sqlalchemy.orm import Session
from sqlalchemy.sql import true as sql_true

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

    # ✅ demo_only: title prefix OR evidence.demo=true 둘 중 하나면 데모로 인정
    if demo_only:
        stmt = stmt.where(
            or_(
                Anomaly.title.ilike("[demo]%"),
                Anomaly.evidence["demo"].as_boolean() == sql_true(),
            )
        )

    if sort == "severity_desc":
        stmt = stmt.order_by(desc(severity_rank_expr()), desc(Anomaly.detected_at))
    else:
        # recent
        stmt = stmt.order_by(desc(Anomaly.detected_at))

    stmt = stmt.limit(limit)
    return cast(list[Anomaly], db.execute(stmt).scalars().all())
