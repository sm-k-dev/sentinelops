from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from sentinelops.models.event import Event


def save_verified_event(
    db: Session,
    *,
    provider_event_id: str,
    event_type: str,
    raw: dict,
    signature: str | None,
) -> dict:
    row = Event(
        source="stripe",
        provider_event_id=provider_event_id,
        event_type=event_type,
        status="verified",
        raw=raw,
        signature=signature,
        livemode=raw.get("livemode"),
        created_at_provider=datetime.fromtimestamp(raw["created"], tz=timezone.utc),
    )

    try:
        db.add(row)
        db.commit()
        return {"saved": True, "deduped": False}
    except IntegrityError:
        db.rollback()
        return {"saved": False, "deduped": True}


def save_invalid_event(
    db: Session,
    *,
    payload: bytes,
    signature: str | None,
    reason: str,
) -> None:
    """
    invalid도 '수신된 사실'로 기록. 실패해도 예외를 밖으로 던지지 않음.
    """
    try:
        row = Event(
            source="stripe",
            provider_event_id=None,
            event_type=None,
            status="invalid",
            raw={
                "error": reason,
                "payload": payload.decode("utf-8", errors="replace"),
            },
            signature=signature,
            # created_at_provider는 검증 실패면 신뢰 못 하니 생략
        )
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()
        # 관측 철학: 저장 실패해도 webhook 2xx 유지
        return
