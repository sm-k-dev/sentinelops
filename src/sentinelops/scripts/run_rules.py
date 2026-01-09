from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from sentinelops.db.session import SessionLocal
from sentinelops.models.event import Event
from sentinelops.models.anomaly import Anomaly
from sentinelops.core.anomaly_rules import RULES


def floor_to_5min(dt: datetime) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    minute_bucket = (dt.minute // 5) * 5
    return dt.replace(minute=minute_bucket)

def floor_to_30min(dt: datetime) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    minute_bucket = (dt.minute // 30) * 30
    return dt.replace(minute=minute_bucket)

def run_webhook_integrity_rule(db: Session):
    now = datetime.now(timezone.utc)

    window_start = floor_to_30min(now)
    window_end = window_start + timedelta(minutes=30)

    invalid_events = (
        db.query(Event)
        .filter(Event.status == "invalid")
        .filter(Event.created_at >= window_start)
        .filter(Event.created_at < window_end)
        .order_by(Event.created_at.desc())
        .limit(5)
        .all()
    )

    if not invalid_events:
        print("No invalid events found.")
        return

    rule = next(r for r in RULES if r.code == "webhook_integrity")

    # ✅ 중복 방지: 같은 버킷 윈도우에 open anomaly가 있으면 스킵
    existing = (
        db.query(Anomaly)
        .filter(Anomaly.rule_code == rule.code)
        .filter(Anomaly.status == "open")
        .filter(Anomaly.window_start == window_start)
        .filter(Anomaly.window_end == window_end)
        .first()
    )
    if existing:
        print(f"Anomaly already exists: {rule.code} (id={existing.id})")
        return

    anomaly = Anomaly(
        rule_code=rule.code,
        severity=rule.severity,
        title=rule.title,
        status="open",
        window_start=window_start,
        window_end=window_end,
        detected_at=now,
        evidence={
            "invalid_event_count": len(invalid_events),
            "sample_event_ids": [e.id for e in invalid_events],
        },
    )

    db.add(anomaly)
    db.commit()
    print(f"Anomaly created: {rule.code}")

def run_payment_failure_spike_rule(db: Session):
    now = datetime.now(timezone.utc)

    window_start = floor_to_30min(now)
    window_end = window_start + timedelta(minutes=30)

    failed_count = (
        db.query(Event)
        .filter(Event.status == "verified")
        .filter(Event.event_type.in_(["payment_intent.payment_failed", "charge.failed"]))
        .filter(Event.created_at >= window_start)
        .filter(Event.created_at < window_end)
        .count()
    )

    THRESHOLD = 3
    if failed_count < THRESHOLD:
        print(f"No failure spike. failed_count={failed_count}")
        return

    rule = next(r for r in RULES if r.code == "payment_failure_spike")

    # ✅ 중복 방지: 같은 버킷 윈도우에 open anomaly가 있으면 스킵
    existing = (
        db.query(Anomaly)
        .filter(Anomaly.rule_code == rule.code)
        .filter(Anomaly.status == "open")
        .filter(Anomaly.window_start == window_start)
        .filter(Anomaly.window_end == window_end)
        .first()
    )
    if existing:
        print(f"Anomaly already exists: {rule.code} (id={existing.id})")
        return

    anomaly = Anomaly(
        rule_code=rule.code,
        severity=rule.severity,
        title=rule.title,
        status="open",
        window_start=window_start,
        window_end=window_end,
        detected_at=now,
        evidence={
            "failed_count": failed_count,
            "threshold": THRESHOLD,
            "window_minutes": 30,
        },
    )
    db.add(anomaly)
    db.commit()
    print(f"Anomaly created: {rule.code}")

def run_rapid_retry_failure_rule(db: Session):
    now = datetime.now(timezone.utc)

    window_start = floor_to_5min(now)
    window_end = window_start + timedelta(minutes=5)

    failed_count = (
        db.query(Event)
        .filter(Event.status == "verified")
        .filter(Event.event_type.in_(["payment_intent.payment_failed", "charge.failed"]))
        .filter(Event.created_at >= window_start)
        .filter(Event.created_at < window_end)
        .count()
    )

    THRESHOLD = 2  # 5분 안에 2번이면 즉시 대응 신호로 보기

    if failed_count < THRESHOLD:
        print(f"No rapid retry failure. failed_count={failed_count}")
        return

    rule = next(r for r in RULES if r.code == "rapid_retry_failure")

    # ✅ 중복 방지 (5분 버킷)
    existing = (
        db.query(Anomaly)
        .filter(Anomaly.rule_code == rule.code)
        .filter(Anomaly.status == "open")
        .filter(Anomaly.window_start == window_start)
        .filter(Anomaly.window_end == window_end)
        .first()
    )
    if existing:
        print(f"Anomaly already exists: {rule.code} (id={existing.id})")
        return

    anomaly = Anomaly(
        rule_code=rule.code,
        severity=rule.severity,
        title=rule.title,
        status="open",
        window_start=window_start,
        window_end=window_end,
        detected_at=now,
        evidence={
            "failed_count": failed_count,
            "threshold": THRESHOLD,
            "window_minutes": 5,
        },
    )
    db.add(anomaly)
    db.commit()
    print(f"Anomaly created: {rule.code}")

def main():
    db = SessionLocal()
    try:
        run_webhook_integrity_rule(db)
        run_payment_failure_spike_rule(db)
        run_rapid_retry_failure_rule(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
