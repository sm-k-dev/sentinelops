from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from sentinelops.db.session import SessionLocal
from sentinelops.models.anomaly import Anomaly

DEMO_TAG = "[demo]"  # title에 붙여서 한눈에 식별
DEMO_EVIDENCE_TAG = {"_demo": True, "_seed_version": 2}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _jittered_detected_at(*, now: datetime) -> datetime:
    """
    데모가 너무 '딱 같은 시간'으로만 찍히면 부자연스러워서
    최근 5~40분 사이로 살짝 흔들어준다.
    """
    minutes_ago = random.randint(5, 40)
    return now - timedelta(minutes=minutes_ago)


def _demo_specs(now: datetime) -> list[dict]:
    """
    현실감:
    - high/medium/low 섞기
    - window 있는 룰 + 없는 룰 섞기
    - evidence에 threshold/window 등 넣기
    """
    detected_at_1 = _jittered_detected_at(now=now)
    detected_at_2 = _jittered_detected_at(now=now)
    detected_at_3 = _jittered_detected_at(now=now)

    return [
        # High: 30m spike
        {
            "rule_code": "payment_failure_spike",
            "severity": "high",
            "title": f"{DEMO_TAG} Payment failure spike",
            "detected_at": detected_at_1,
            "window_minutes": 30,
            "evidence": {
                "failed_count": 7,
                "threshold": 3,
                "window_minutes": 30,
                "note": "Demo seed anomaly",
                **DEMO_EVIDENCE_TAG,
            },
        },
        # Medium: 5m rapid retry
        {
            "rule_code": "rapid_retry_failure",
            "severity": "medium",
            "title": f"{DEMO_TAG} Rapid payment failure retries (5m)",
            "detected_at": detected_at_2,
            "window_minutes": 5,
            "evidence": {
                "failed_count": 4,
                "threshold": 2,
                "window_minutes": 5,
                "note": "Demo seed anomaly",
                **DEMO_EVIDENCE_TAG,
            },
        },
        # Low: webhook integrity (window 없음도 자연스러움)
        {
            "rule_code": "webhook_integrity",
            "severity": "low",
            "title": f"{DEMO_TAG} Webhook integrity anomaly",
            "detected_at": detected_at_3,
            "window_minutes": None,
            "evidence": {
                "invalid_event_count": 2,
                "sample_event_ids": [101, 102],
                "note": "Demo seed anomaly",
                **DEMO_EVIDENCE_TAG,
            },
        },
    ]


def _close_existing_demo_open(db: Session) -> int:
    """
    기존에 남아있는 demo open들을 정리(resolved)해서
    데모를 '항상 동일한 3개 open'으로 맞출 수 있게 한다.
    """
    rows = (
        db.query(Anomaly)
        .filter(Anomaly.status == "open")
        .filter(Anomaly.title.like(f"{DEMO_TAG}%"))
        .all()
    )

    if not rows:
        return 0

    now = _now()
    for r in rows:
        r.status = "resolved"
        # 기존 lifecycle 규칙과 최대한 비슷하게
        if getattr(r, "acknowledged_at", None) is None:
            r.acknowledged_at = now
        r.resolved_at = now

    db.commit()
    return len(rows)


def _ensure_open_by_rule_code(db: Session, spec: dict) -> None:
    """
    rule_code 기준으로 open이 이미 있으면 스킵.
    단, demo title을 가진 open이 아니라면(실데이터 open) 건드리지 않는다.
    """
    rule_code = spec["rule_code"]

    existing_open = (
        db.query(Anomaly)
        .filter(Anomaly.rule_code == rule_code)
        .filter(Anomaly.status == "open")
        .first()
    )

    if existing_open:
        print(f"⏭️ Open anomaly already exists: {rule_code} (id={existing_open.id})")
        return

    window_start = None
    window_end = None

    if spec["window_minutes"]:
        window_end = spec["detected_at"]
        window_start = window_end - timedelta(minutes=int(spec["window_minutes"]))

    anomaly = Anomaly(
        rule_code=rule_code,
        severity=spec["severity"],
        title=spec["title"],
        status="open",
        window_start=window_start,
        window_end=window_end,
        detected_at=spec["detected_at"],
        evidence=spec["evidence"],
    )

    db.add(anomaly)
    db.commit()
    db.refresh(anomaly)

    print(f"✅ Demo anomaly created: {anomaly.rule_code} (id={anomaly.id})")


def seed_demo_anomalies(db: Session, *, reset_demo: bool) -> None:
    now = _now()

    if reset_demo:
        closed = _close_existing_demo_open(db)
        if closed:
            print(f"🧹 Closed existing demo open anomalies: {closed}")

    specs = _demo_specs(now)
    for spec in specs:
        _ensure_open_by_rule_code(db, spec)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed deterministic demo anomalies for SentinelOps")
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Resolve existing [demo] open anomalies before seeding new ones",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        seed_demo_anomalies(db, reset_demo=bool(args.reset_demo))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
