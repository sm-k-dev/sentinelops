import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
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

    # 1) signature verification
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 2) store (idempotent by provider_event_id unique)
    evt_id = event["id"]
    evt_type = event["type"]

    row = Event(
        source="stripe",
        provider_event_id=evt_id,
        event_type=evt_type,
        raw=payload.decode("utf-8"),
    )

    try:
        db.add(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        # already received -> return 200 so Stripe doesn't retry
        return Response(status_code=200)

    return Response(status_code=200)
