from dataclasses import dataclass
from typing import Literal

Severity = Literal["low", "medium", "high"]

# Anomaly rule은 단순 문자열 묶음이 아니라 - rule_code, severity, title, description 등 메타정보가 필요
# 나중엔 threshold, window, enabled 등도 추가될 수 있음, 즉 구조화된 개념(개체)으로 다룸
# dict도 가능하지만 지저분해진다. class/dataclass로 깔끔하게.

# 타입 (설계도)
@dataclass(frozen=True)
class RuleDef:
    code: str
    severity: Severity
    title: str
    description: str

# 실제 룰 인스턴스 (데이터)
RULES: list[RuleDef] = [
    RuleDef(
        code="payment_failure_spike",
        severity="high",
        title="Payment failure spike",
        description="결제 실패율이 최근 구간에서 기준 대비 급증",
    ),
    RuleDef(
        code="refund_spike",
        severity="high",
        title="Refund spike",
        description="환불 건수/금액이 기준 대비 급증",
    ),
    RuleDef(
        code="churn_spike",
        severity="high",
        title="Churn spike / subscription loss",
        description="구독 해지 또는 인보이스 실패가 기준 대비 급증",
    ),
    RuleDef(
        code="amount_spike",
        severity="medium",
        title="Amount spike",
        description="단일 결제 금액이 최근 30일 평균 대비 과도하게 큼",
    ),
    RuleDef(
        code="webhook_integrity",
        severity="low",
        title="Webhook integrity anomaly",
        description="invalid / deduped / 지연 등 webhook 관측 품질 이상",
    ),
    RuleDef(
        code="rapid_retry_failure",
        severity="high",
        title="Rapid payment failure retries (5m)",
        description="Multiple payment failures detected within 5 minutes, possible checkout issue or card declines spike.",
    )
]
