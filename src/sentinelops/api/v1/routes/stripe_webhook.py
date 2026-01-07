import json

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
        # 이 줄이 있으면 원인 파악이 훨씬 쉬워져
        raise HTTPException(status_code=400, detail=f"Invalid signature: {e}")
    
    provider_event_id = event["id"]
    event_type = event["type"]
    # raw_json = json.dumps(event, default=str)

    # 2) Save
    row = Event(
        source="stripe",
        provider_event_id=provider_event_id,
        event_type=event_type,
        # raw=raw_json,
        raw=event,
    )

    # 3) Idempotency: 이미 저장된 이벤트면 스킵
    try:
        db.add(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"ok": True, "deduped": True, "provider_event_id": provider_event_id}

    return {"ok": True, "saved": True, "provider_event_id": provider_event_id, "event_type": event_type}
