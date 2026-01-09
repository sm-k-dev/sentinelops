from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from sentinelops.api.deps import db_session
from sentinelops.integrations.stripe.webhook import construct_event
from sentinelops.services.events_ingest import save_invalid_event, save_verified_event

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

    # 1) Verify + parse
    try:
        event = construct_event(payload, stripe_signature)
    except Exception as e:
        # ✅ invalid도 "수신된 사실"로 남긴다
        save_invalid_event(db, payload=payload, signature=stripe_signature, reason=str(e))
        return {"ok": False, "invalid": True, "reason": str(e)}

    provider_event_id = event["id"]
    event_type = event["type"]

    # 2) Save (idempotent)
    result = save_verified_event(
        db,
        provider_event_id=provider_event_id,
        event_type=event_type,
        raw=event,
        signature=stripe_signature,
    )

    if result["deduped"]:
        return {"ok": True, "deduped": True, "provider_event_id": provider_event_id}

    return {"ok": True, "saved": True, "provider_event_id": provider_event_id, "event_type": event_type}
