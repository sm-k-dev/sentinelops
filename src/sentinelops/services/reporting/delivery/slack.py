from __future__ import annotations

import requests

from sentinelops.core.config import settings


def post_to_slack(text: str) -> str:
    """
    Slack Incoming Webhook으로 전송하고 응답 body(text)를 반환한다.
    """
    webhook = settings.slack_webhook_url
    webhook_url = webhook.get_secret_value() if webhook else None
    if not webhook_url:
        raise RuntimeError("SLACK_WEBHOOK_URL is not set")

    resp = requests.post(webhook_url, json={"text": text}, timeout=10)
    if resp.status_code >= 400:
        raise RuntimeError(f"Slack webhook failed: {resp.status_code} {resp.text}")

    return (resp.text or "").strip()
