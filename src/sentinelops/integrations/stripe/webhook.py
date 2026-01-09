import stripe
from sentinelops.core.config import settings


def construct_event(payload: bytes, signature: str) -> dict:
    """
    Stripe signature 검증 + event 파싱.
    실패 시 예외 발생.
    """
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=settings.stripe_webhook_secret,
    )
