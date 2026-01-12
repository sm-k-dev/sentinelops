from __future__ import annotations

"""
SentinelOps v0.4 - Daily Ops Summary Aggregation

목표
- 지난 24시간(또는 지정 window) 동안의 운영 신호를 "집계된 형태"로 모아 DailySummaryInput을 생성한다.
- v0.4 원칙: Raw Stripe payload를 AI/요약 레이어로 넘기지 않는다.
  -> Aggregated metrics + rule signals(anomalies)만 만든다.

중요 (get_db 관련)
- sentinelops.db.session.get_db()는 FastAPI dependency에서 흔히 쓰는 "generator(yield Session)" 패턴이다.
- 따라서 `with get_db() as session:` 은 불가능 (context manager가 아님).
- scripts/services 레이어에서는 `session = next(get_db())` + `try/finally session.close()`를 사용한다.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sentinelops.db.session import get_db  # ✅ generator dependency
from sentinelops.models.anomaly import Anomaly
from sentinelops.models.event import Event


# -------------------------
# Data Contracts
# -------------------------

@dataclass(frozen=True)
class RuleSignal:
    """
    Rule engine이 만든 anomaly들을 daily window 기준으로 모아 '신호'로 표현한다.
    """
    rule_code: str
    severity: str  # "low" | "medium" | "high"
    hit_count: int
    baseline: int | None = None
    evidence: dict[str, Any] | None = None


@dataclass(frozen=True)
class DailyMetrics:
    """
    Daily Summary에서 항상 유용한 기본 운영 지표.
    - total_events: window 내 들어온 이벤트 수
    - failure_rate_percent: 여기서는 "invalid event rate"로 정의 (명확하고 안정적)
    """
    total_events: int
    failure_rate_percent: float | None = None  # invalid event rate (%)


@dataclass(frozen=True)
class DailySummaryInput:
    """
    compose/reporting/ai 레이어로 넘길 '통제된 입력 데이터'
    - raw payload 없음
    - 계산/집계는 여기서 끝낸다 (AI가 계산하지 않게)
    """
    window_start: datetime
    window_end: datetime
    signals: list[RuleSignal]
    metrics: DailyMetrics

    # 운영 리포트에 자주 필요한 보조 정보
    top_event_types: list[tuple[str, int]]
    open_anomalies_count: int


# -------------------------
# Query Helpers (ORM)
# -------------------------

def _count_events(session: Session, window_start: datetime, window_end: datetime) -> int:
    """
    events.created_at 기준 window 내 total events
    """
    stmt = (
        select(func.count())
        .select_from(Event)
        .where(Event.created_at >= window_start, Event.created_at < window_end)
    )
    return int(session.execute(stmt).scalar_one())


def _count_invalid_events(session: Session, window_start: datetime, window_end: datetime) -> int:
    """
    v0.4 기본 failure_rate 정의:
    - Event.status == "invalid" 비율 (무결성/보안/운영 관점에서 확실한 신호)

    장점:
    - event_type 종류/정의에 의존하지 않음
    - 이미 모델에서 invalid 저장을 고려해 둔 상태라 신뢰도가 높음
    """
    stmt = (
        select(func.count())
        .select_from(Event)
        .where(
            Event.created_at >= window_start,
            Event.created_at < window_end,
            Event.status == "invalid",
        )
    )
    return int(session.execute(stmt).scalar_one())


def _aggregate_rule_signals(session: Session, window_start: datetime, window_end: datetime) -> list[RuleSignal]:
    """
    anomalies.detected_at 기준 window 내 (rule_code, severity)별 hit_count 집계.

    왜 detected_at을 쓰나?
    - Anomaly.window_start/end는 nullable이고, rule별 의미가 다를 수 있음
    - 'Daily ops'는 "그날 탐지된 이상징후"를 보고 싶기 때문에 detected_at이 더 일관적
    """
    stmt = (
        select(
            Anomaly.rule_code,
            Anomaly.severity,
            func.count().label("hit_count"),
        )
        .where(Anomaly.detected_at >= window_start, Anomaly.detected_at < window_end)
        .group_by(Anomaly.rule_code, Anomaly.severity)
        .order_by(func.count().desc())
    )

    rows = session.execute(stmt).all()

    signals: list[RuleSignal] = []
    for rule_code, severity, hit_count in rows:
        signals.append(
            RuleSignal(
                rule_code=str(rule_code),
                severity=str(severity),
                hit_count=int(hit_count),
                baseline=None,   # (선택) baseline을 따로 저장/계산한다면 채우기
                evidence=None,   # (선택) 요약에 쓸 근거가 있으면 채우기
            )
        )
    return signals


def _optional_top_event_types(session: Session, window_start: datetime, window_end: datetime, limit: int = 5) -> list[tuple[str, int]]:
    """
    window 내 event_type Top N
    - Daily ops에서 "어제 뭐가 많이 들어왔지?"를 한 줄로 보여줄 수 있음
    - Slack 스팸 방지를 위해 compose 단계에서 top 1~2 정도만 쓰는 걸 추천
    """
    stmt = (
        select(Event.event_type, func.count().label("cnt"))
        .where(Event.created_at >= window_start, Event.created_at < window_end)
        .group_by(Event.event_type)
        .order_by(func.count().desc())
        .limit(limit)
    )

    rows = session.execute(stmt).all()

    out: list[tuple[str, int]] = []
    for event_type, cnt in rows:
        if event_type is None:
            # provider_event_id가 null인 invalid 저장도 있어서 event_type이 null일 수 있음
            continue
        out.append((str(event_type), int(cnt)))
    return out


def _count_open_anomalies(session: Session, window_start: datetime, window_end: datetime) -> int:
    """
    window 내 새로 탐지된 anomaly 중 아직 open인 것의 수.
    - 운영자 입장에서는 "미처리 이슈가 있나?"를 바로 파악 가능
    """
    stmt = (
        select(func.count())
        .select_from(Anomaly)
        .where(
            Anomaly.detected_at >= window_start,
            Anomaly.detected_at < window_end,
            Anomaly.status == "open",
        )
    )
    return int(session.execute(stmt).scalar_one())


# -------------------------
# Public API
# -------------------------

def collect_daily_summary_input(window_start: datetime, window_end: datetime) -> DailySummaryInput:
    """
    Daily Summary 입력을 구성한다.

    ⚠️ 주의:
    - get_db()는 generator이므로 with 사용 불가
    - 아래처럼 next(get_db()) + finally close를 사용해야 함
    """
    session = next(get_db())
    try:
        # 1) 기본 운영 지표
        total_events = _count_events(session, window_start, window_end)

        invalid_events = _count_invalid_events(session, window_start, window_end) if total_events > 0 else 0
        invalid_rate = round((invalid_events / total_events) * 100, 2) if total_events > 0 else None
        metrics = DailyMetrics(total_events=total_events, failure_rate_percent=invalid_rate)

        # 2) Rule signals (anomalies 기반)
        signals = _aggregate_rule_signals(session, window_start, window_end)

        # 3) 보조 운영 정보
        top_event_types = _optional_top_event_types(session, window_start, window_end, limit=5)
        open_anomalies_count = _count_open_anomalies(session, window_start, window_end)

        return DailySummaryInput(
            window_start=window_start,
            window_end=window_end,
            signals=signals,
            metrics=metrics,
            top_event_types=top_event_types,
            open_anomalies_count=open_anomalies_count,
        )
    finally:
        # generator 세션은 직접 close 해야 함
        session.close()
