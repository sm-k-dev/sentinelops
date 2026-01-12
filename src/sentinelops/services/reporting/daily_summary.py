from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from typing import Optional, Any

from sqlalchemy.orm import Session

from sentinelops.db.session import get_db
from sentinelops.services.reporting.compose import compose_report
from sentinelops.services.reporting.ai_insight import generate_ai_insight

# ✅ 너 프로젝트 실제 모델 위치에 맞게 필요하면 이 import만 조정
from sentinelops.models.daily_summary_delivery import DailySummaryDelivery  # type: ignore

from sentinelops.services.reporting.delivery.slack import post_to_slack


@dataclass(frozen=True)
class DailySummaryResult:
    delivered: bool
    skipped: bool
    skip_reason: Optional[str]
    used_ai: bool
    ai_error: Optional[str]          # ✅ DB에는 코드만
    message_preview: str


def _env_truthy(name: str) -> bool:
    v = (str(getattr(__import__("os"), "environ").get(name, "")) or "").strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def _summary_window(now: datetime) -> tuple[datetime, datetime, date]:
    # last 24h window
    window_end = now
    window_start = now - timedelta(hours=24)
    summary_date = now.date()
    return window_start, window_end, summary_date


def _begin_delivery_or_skip(
    db: Session,
    *,
    kind: str,
    summary_date: date,
    window_start: datetime,
    window_end: datetime,
) -> tuple[Optional[DailySummaryDelivery], Optional[str]]:
    force_resend = _env_truthy("FORCE_RESEND_DAILY_SUMMARY")

    existing = (
        db.query(DailySummaryDelivery)
        .filter(DailySummaryDelivery.kind == kind)
        .filter(DailySummaryDelivery.summary_date == summary_date)
        .one_or_none()
    )

    if existing and not force_resend:
        return None, "already_sent"

    if existing and force_resend:
        # 재전송이면 기존 레코드 재사용(업데이트)
        existing.window_start = window_start
        existing.window_end = window_end
        existing.status = "sending"
        existing.used_ai = False
        existing.ai_error = None
        existing.slack_response = None
        db.commit()
        return existing, None

    rec = DailySummaryDelivery(
        kind=kind,
        summary_date=summary_date,
        status="sending",
        window_start=window_start,
        window_end=window_end,
        delivered_at=None,
        used_ai=False,
        ai_error=None,
        slack_response=None,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec, None


def _finalize_record(
    db: Session,
    record: DailySummaryDelivery,
    *,
    status: str,
    delivered_at: Optional[datetime],
    used_ai: bool,
    ai_error: Optional[str],          # ✅ 코드만 저장
    slack_response: Optional[str],
) -> None:
    record.status = status
    record.delivered_at = delivered_at
    record.used_ai = used_ai
    record.ai_error = ai_error
    record.slack_response = slack_response

    db.commit()


def _compose_slack_message(
    *,
    summary_date: date,
    overall: str,
    highlights: list[str],
    watch_list: list[str],
    ai_text: Optional[str],
    ai_error_code: Optional[str],
) -> str:
    # Slack 출력: 기존 스타일 유지
    lines: list[str] = []
    lines.append(f"🗓 Daily Ops Summary – {summary_date.isoformat()}")
    lines.append("")
    lines.append("Overall:")
    lines.append(overall)
    lines.append("")
    lines.append("Highlights:")
    for h in highlights:
        lines.append(f"• {h}")

    if watch_list:
        lines.append("")
        lines.append("Watch:")
        for w in watch_list:
            lines.append(f"• {w}")

    if ai_text:
        lines.append("")
        lines.append("AI Insight:")
        lines.append(ai_text)

    # ✅ 옵션일 때만 조용히 1줄 추가
    if (not ai_text) and ai_error_code and _env_truthy("SHOW_AI_UNAVAILABLE_NOTE"):
        lines.append(f"AI: unavailable ({ai_error_code})")

    return "\n".join(lines).strip() + "\n"


def _collect_daily_summary_input_compat(
    db: Session,
    window_start: datetime,
    window_end: datetime,
) -> Any:
    """
    aggregation.collect_daily_summary_input 시그니처가 바뀌어도 여기서 흡수.
    - db를 받는 버전 / 안 받는 버전 둘 다 대응
    """
    from sentinelops.services.reporting import aggregation as aggregation_mod  # 로컬 import

    fn = getattr(aggregation_mod, "collect_daily_summary_input")
    try:
        return fn(db, window_start, window_end)
    except TypeError:
        return fn(window_start, window_end)


def run_daily_ops_summary(*, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    window_start, window_end, summary_date = _summary_window(now)

    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        record, skip_reason = _begin_delivery_or_skip(
            db,
            kind="daily_ops",
            summary_date=summary_date,
            window_start=window_start,
            window_end=window_end,
        )

        if skip_reason:
            return {
                "delivered": False,
                "skipped": True,
                "skip_reason": skip_reason,
                "used_ai": False,
                "ai_error": None,
                "message_preview": "",
            }

        assert record is not None

        # 1) aggregate
        daily_input = _collect_daily_summary_input_compat(db, window_start, window_end)

        # 2) compose
        report = compose_report(daily_input)

        # 3) AI (optional)
        ai_text: Optional[str] = None
        ai_used = False
        ai_error_code: Optional[str] = None
        ai_error_detail: Optional[str] = None

        ai_result = generate_ai_insight(report.ai_payload)
        if ai_result.summary_text:
            ai_text = ai_result.summary_text
            ai_used = True
        else:
            ai_error_code = ai_result.error_code
            ai_error_detail = ai_result.error_detail

        # ✅ 상세는 콘솔 로그에만
        if ai_error_code:
            if ai_error_detail:
                # 길어도 괜찮게 1줄 요약해서 찍기
                one_line = " ".join(ai_error_detail.split())
                if len(one_line) > 220:
                    one_line = one_line[:220] + "…"
                print(f"AI insight error: {ai_error_code} ({one_line})")
            else:
                print(f"AI insight error: {ai_error_code}")

        msg = _compose_slack_message(
            summary_date=summary_date,
            overall=report.overall_status,
            highlights=report.highlights,
            watch_list=report.watch_list,
            ai_text=ai_text,
            ai_error_code=ai_error_code,
        )

        # 4) deliver
        resp_text = post_to_slack(msg)  # "ok" 같은 응답

        # 5) finalize (✅ DB에는 ai_error_code만)
        _finalize_record(
            db,
            record,
            status="sent",
            delivered_at=datetime.now(timezone.utc),
            used_ai=ai_used,
            ai_error=ai_error_code,
            slack_response=(resp_text or "")[:100],  # slack_response가 VARCHAR(100)이면 안전하게
        )

        return {
            "delivered": True,
            "skipped": False,
            "skip_reason": None,
            "used_ai": ai_used,
            "ai_error": ai_error_code,
            "message_preview": msg.strip(),
        }

    except Exception:
        # 세션이 꼬였을 수 있어서 안전하게 롤백
        try:
            db.rollback()
        except Exception:
            pass
        raise

    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
