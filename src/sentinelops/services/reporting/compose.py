from __future__ import annotations

"""
SentinelOps v0.4 - Compose Layer

역할
- aggregation.py에서 생성된 DailySummaryInput(집계된 입력)을
  운영 리포트 형태(Overall / Highlights / Watch)로 정리한다.
- 여기서는 "새로운 판단"을 만들지 않는다.
  - severity 판정은 rule engine(anomaly_rules.py)의 결과를 따른다.
  - compose는 severity를 '집계/요약(max severity)'만 한다.
- Slack 스팸 방지: highlights 길이 제한

출력
- ComposedReport: overall_status, highlights, watch_list, ai_payload
"""

from dataclasses import dataclass
from typing import Any, Literal

from .aggregation import DailySummaryInput, RuleSignal

Severity = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ComposedReport:
    overall_status: str
    highlights: list[str]
    watch_list: list[str]
    ai_payload: dict[str, Any]


def _severity_rank(sev: str) -> int:
    """
    severity 문자열은 rule engine이 만든 값을 그대로 사용한다.
    여기서는 정렬/집계 목적의 rank만 정의.
    """
    return {"high": 3, "medium": 2, "low": 1}.get(sev, 0)


def _sort_signals(signals: list[RuleSignal]) -> list[RuleSignal]:
    # severity 우선(높을수록 먼저) + hit_count 큰 순
    return sorted(signals, key=lambda s: (-_severity_rank(s.severity), -s.hit_count))


def _max_severity(signals: list[RuleSignal]) -> str:
    """
    AI 톤/보고서 요약을 위해, window 내 최고 severity를 계산한다.
    - 판정(기준)은 rule engine이 함
    - compose는 결과를 집계할 뿐
    """
    best = "low"
    best_rank = 0
    for s in signals:
        r = _severity_rank(s.severity)
        if r > best_rank:
            best_rank = r
            best = s.severity
    return best if best_rank > 0 else "low"


def _build_overall_status(signals_sorted: list[RuleSignal], open_anomalies_count: int) -> str:
    """
    Overall은 deterministic하게(규칙 기반) 만든다.
    - AI에 Overall 판단을 맡기지 않는다.
    """
    if any(s.severity == "high" for s in signals_sorted):
        return "System had critical anomalies in the last 24 hours."
    if any(s.severity == "medium" for s in signals_sorted):
        return "System was mostly stable with minor anomalies."
    if open_anomalies_count > 0:
        return "System was stable, but there are open anomalies to review."
    return "System was stable in the last 24 hours."


def compose_report(daily_input: DailySummaryInput) -> ComposedReport:
    signals_sorted = _sort_signals(daily_input.signals)
    max_sev = _max_severity(signals_sorted)

    overall = _build_overall_status(signals_sorted, daily_input.open_anomalies_count)

    highlights: list[str] = []
    watch: list[str] = []

    # ---- (A) 운영자가 항상 궁금해하는 지표 ----
    highlights.append(f"Open anomalies: {daily_input.open_anomalies_count}")
    highlights.append(f"Total events: {daily_input.metrics.total_events}")

    if daily_input.metrics.failure_rate_percent is not None:
        highlights.append(f"Invalid event rate: {daily_input.metrics.failure_rate_percent}%")

    # Top event types (상위 2개만 표시)
    if daily_input.top_event_types:
        top2 = daily_input.top_event_types[:2]
        top_text = ", ".join([f"{t}({c})" for t, c in top2])
        highlights.append(f"Top event types: {top_text}")

    # ---- (B) 룰 시그널 상위 3개 ----
    for s in signals_sorted[:3]:
        line = f"{s.rule_code}: {s.hit_count} hits"
        if s.baseline is not None:
            line += f" (baseline {s.baseline})"
        highlights.append(line)

    # ---- (C) watch list: 다음 우선순위 시그널 몇 개 ----
    for s in signals_sorted[3:6]:
        watch.append(f"{s.rule_code}: monitor trend (hits {s.hit_count})")

    # Slack 스팸 방지: highlights를 너무 길게 하지 않음
    highlights = highlights[:6]

    ai_payload: dict[str, Any] = {
        "summary_window": "last_24_hours",
        "window_start": daily_input.window_start.isoformat(),
        "window_end": daily_input.window_end.isoformat(),
        # ✅ AI 톤 힌트(판정은 rule engine 결과 집계)
        "max_severity": max_sev,
        "open_anomalies_count": daily_input.open_anomalies_count,
        "top_event_types": [{"event_type": t, "count": c} for t, c in daily_input.top_event_types],
        "rules_triggered": [
            {
                "rule_code": s.rule_code,
                "severity": s.severity,
                "hit_count": s.hit_count,
                "baseline": s.baseline,
            }
            for s in signals_sorted
        ],
        "system_metrics": {
            "total_events": daily_input.metrics.total_events,
            "invalid_event_rate_percent": daily_input.metrics.failure_rate_percent,
        },
    }

    return ComposedReport(
        overall_status=overall,
        highlights=highlights,
        watch_list=watch,
        ai_payload=ai_payload,
    )
