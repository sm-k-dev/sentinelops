from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy.sql import true as sql_true

from sentinelops.db.session import SessionLocal
from sentinelops.models.anomaly import Anomaly


def _floor_to_minutes(dt: datetime, minutes: int) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    bucket = (dt.minute // minutes) * minutes
    return dt.replace(minute=bucket)


def _demo_open_exists(db: Session, rule_code: str) -> Anomaly | None:
    # ✅ demo를 title prefix 또는 evidence.demo=true 둘 중 하나로 판정
    return (
        db.query(Anomaly)
        .filter(Anomaly.rule_code == rule_code)
        .filter(Anomaly.status == "open")
        .filter(
            (Anomaly.title.ilike("[demo]%")) | (Anomaly.evidence["demo"].as_boolean() == sql_true())
        )
        .order_by(Anomaly.detected_at.desc())
        .first()
    )


def _create_demo_anomaly(
    db: Session,
    *,
    rule_code: str,
    severity: str,
    title: str,
    window_minutes: int | None,
    evidence: dict,
) -> Anomaly:
    now = datetime.now(timezone.utc)

    window_start = None
    window_end = None
    if window_minutes is not None:
        window_start = _floor_to_minutes(now, window_minutes)
        window_end = window_start + timedelta(minutes=window_minutes)

    row = Anomaly(
        rule_code=rule_code,
        severity=severity,
        title=title,
        status="open",
        window_start=window_start,
        window_end=window_end,
        detected_at=now,
        evidence=evidence,
    )

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def main() -> int:
    db = SessionLocal()
    try:
        # 1) payment_failure_spike (30m)
        code = "payment_failure_spike"
        existing = _demo_open_exists(db, code)
        if existing:
            print(f"⏭️ Open demo anomaly already exists: {code} (id={existing.id})")
        else:
            row = _create_demo_anomaly(
                db,
                rule_code=code,
                severity="high",
                title="[demo] Payment failure spike (30m)",
                window_minutes=30,
                evidence={
                    "demo": True,
                    "window_minutes": 30,
                    "threshold": 3,
                    "failed_count": 5,
                    "note": "Seeded for demo lifecycle (open → ack → resolve).",
                },
            )
            print(f"✅✅ Demo anomaly created: {code} (id={row.id})")

        # 2) rapid_retry_failure (5m)
        code = "rapid_retry_failure"
        existing = _demo_open_exists(db, code)
        if existing:
            print(f"⏭️ Open demo anomaly already exists: {code} (id={existing.id})")
        else:
            row = _create_demo_anomaly(
                db,
                rule_code=code,
                severity="medium",
                title="[demo] Rapid payment failure retries (5m)",
                window_minutes=5,
                evidence={
                    "demo": True,
                    "window_minutes": 5,
                    "threshold": 2,
                    "failed_count": 3,
                    "note": "Seeded for demo. Represents short-window burst failures.",
                },
            )
            print(f"✅✅ Demo anomaly created: {code} (id={row.id})")

        # 3) webhook_integrity (30m) - invalid webhook signals
        code = "webhook_integrity"
        existing = _demo_open_exists(db, code)
        if existing:
            print(f"⏭️ Open demo anomaly already exists: {code} (id={existing.id})")
        else:
            row = _create_demo_anomaly(
                db,
                rule_code=code,
                severity="low",
                title="[demo] Webhook integrity anomaly",
                window_minutes=30,
                evidence={
                    "demo": True,
                    "window_minutes": 30,
                    "invalid_event_count": 3,
                    "sample_event_ids": [101, 102, 103],
                    "note": "Seeded for demo. Simulates invalid signature / malformed events.",
                },
            )
            print(f"✅✅ Demo anomaly created: {code} (id={row.id})")

        return 0

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
