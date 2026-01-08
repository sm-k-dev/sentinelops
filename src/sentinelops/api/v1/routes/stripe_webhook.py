import json
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sentinelops.api.deps import db_session
from sentinelops.core.config import settings
from sentinelops.models.event import Event

router = APIRouter(prefix="/stripe", tags=["stripe"])


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(db_session),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    # Stripe 웹훅은 실패하면 재시도가 폭탄처럼 올 수 있어서,
    # SentinelOps는 "가능하면 기록하고 2xx로 응답" 쪽에 무게를 둔다.
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    payload = await request.body()

    # 1) Verify signature
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except Exception as e:
        # ✅ SentinelOps 관측 철학: invalid도 "수신된 사실"로 남긴다
        # - 검증 실패면 evt_id를 신뢰할 수 없으므로 provider_event_id는 None 처리
        # - event_type도 None (또는 "unknown")으로 둔다
        # - raw에는 에러 + payload를 함께 저장해서 디버깅 가능하게 만든다
        try:
            invalid_row = Event(
                source="stripe",
                provider_event_id=None,  # 중요: 검증 실패면 evt_id를 신뢰할 수 없음
                event_type=None,         # 또는 "unknown"
                status="invalid",
                signature=stripe_signature,
                raw={
                    "error": str(e),
                    "payload": payload.decode("utf-8", errors="replace"),
                },
                # created_at은 DB server_default(func.now())로 자동 생성
            )
            db.add(invalid_row)
            db.commit()
        except Exception:
            db.rollback()
            # DB 저장 실패해도 2xx 유지 (재시도 폭탄 방지 목적)
            pass

        # ✅ 응답은 2xx (FastAPI는 dict 반환 시 200)
        return {"ok": False, "invalid": True, "reason": str(e)}

    provider_event_id = event["id"]
    event_type = event["type"]
    # raw_json = json.dumps(event, default=str)

    # 2) Save verified event
    row = Event(
        source="stripe",
        provider_event_id=provider_event_id,
        event_type=event_type,
        status="verified",
        raw=event,  # JSONB에 dict로 저장
        signature=stripe_signature,
        livemode=event.get("livemode"),
        created_at_provider=datetime.fromtimestamp(event["created"], tz=timezone.utc),
    )

    # 3) Idempotency
    # - UNIQUE(provider_event_id)로 중복 방지
    # - Stripe 재시도/동시성 상황에서도 IntegrityError 캐치로 안전
    try:
        db.add(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"ok": True, "deduped": True, "provider_event_id": provider_event_id}

    return {
        "ok": True,
        "saved": True,
        "provider_event_id": provider_event_id,
        "event_type": event_type,
    }
