from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from sentinelops.core.anomaly_rules import RULES
from sentinelops.models.anomaly import Anomaly
from sentinelops.models.event import Event
from sentinelops.services.notifications.slack import send_slack_message
from sentinelops.services.notifications.templates import anomaly_to_slack_text


# -----------------------------
# Time bucket helpers
# -----------------------------
def floor_to_5min(dt: datetime) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    minute_bucket = (dt.minute // 5) * 5
    return dt.replace(minute=minute_bucket)


def floor_to_30min(dt: datetime) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    minute_bucket = (dt.minute // 30) * 30
    return dt.replace(minute=minute_bucket)


# -----------------------------
# Common helpers
# -----------------------------
def _rule_by_code(code: str):
    # RULES는 작아서 next(...)로도 충분. 커지면 dict로 캐시해도 됨.
    return next(r for r in RULES if r.code == code)


def _find_existing_open_anomaly(
    db: Session,
    *,
    rule_code: str,
    window_start: Optional[datetime],
    window_end: Optional[datetime],
) -> Optional[Anomaly]:
    q = (
        db.query(Anomaly)
        .filter(Anomaly.rule_code == rule_code)
        .filter(Anomaly.status == "open")
    )
    if window_start is not None:
        q = q.filter(Anomaly.window_start == window_start)
    if window_end is not None:
        q = q.filter(Anomaly.window_end == window_end)
    return q.first()


def _create_open_anomaly(
    db: Session,
    *,
    rule_code: str,
    title: str,
    severity: str,
    now: datetime,
    window_start: Optional[datetime],
    window_end: Optional[datetime],
    evidence: dict[str, Any],
) -> Anomaly:
    anomaly = Anomaly(
        rule_code=rule_code,
        severity=severity,
        title=title,
        status="open",
        window_start=window_start,
        window_end=window_end,
        detected_at=now,
        evidence=evidence,
    )

    db.add(anomaly)
    db.commit()
    db.refresh(anomaly)
    return anomaly


def _create_once_and_notify(
    db: Session,
    *,
    rule_code: str,
    window_start: Optional[datetime],
    window_end: Optional[datetime],
    evidence: dict[str, Any],
    now: datetime,
):
    # ✅ 중복 방지: 같은 rule_code + 같은 window + open 존재하면 스킵
    existing = _find_existing_open_anomaly(
        db, rule_code=rule_code, window_start=window_start, window_end=window_end
    )
    if existing:
        print(f"Anomaly already exists: {rule_code} (id={existing.id})")
        return

    rule = _rule_by_code(rule_code)
    anomaly = _create_open_anomaly(
        db,
        rule_code=rule.code,
        title=rule.title,
        severity=rule.severity,
        now=now,
        window_start=window_start,
        window_end=window_end,
        evidence=evidence,
    )

    # side effect
    send_slack_message(anomaly_to_slack_text(anomaly))
    print(f"Anomaly created: {rule_code} (id={anomaly.id})")


# -----------------------------
# Rules
# -----------------------------
def run_webhook_integrity_rule(db: Session) -> None:
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

    _create_once_and_notify(
        db,
        rule_code="webhook_integrity",
        window_start=window_start,
        window_end=window_end,
        now=now,
        evidence={
            "invalid_event_count": len(invalid_events),
            "sample_event_ids": [e.id for e in invalid_events],
        },
    )


def run_payment_failure_spike_rule(db: Session) -> None:
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

    _create_once_and_notify(
        db,
        rule_code="payment_failure_spike",
        window_start=window_start,
        window_end=window_end,
        now=now,
        evidence={
            "failed_count": failed_count,
            "threshold": THRESHOLD,
            "window_minutes": 30,
        },
    )


def run_rapid_retry_failure_rule(db: Session) -> None:
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

    THRESHOLD = 2  # 5분 안에 2번이면 즉시 대응 신호
    if failed_count < THRESHOLD:
        print(f"No rapid retry failure. failed_count={failed_count}")
        return

    _create_once_and_notify(
        db,
        rule_code="rapid_retry_failure",
        window_start=window_start,
        window_end=window_end,
        now=now,
        evidence={
            "failed_count": failed_count,
            "threshold": THRESHOLD,
            "window_minutes": 5,
        },
    )


def run_all_rules(db: Session) -> None:
    # 여기서 순서만 관리하면 됨
    run_webhook_integrity_rule(db)
    run_payment_failure_spike_rule(db)
    run_rapid_retry_failure_rule(db)
