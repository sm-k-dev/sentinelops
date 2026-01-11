import requests
from sentinelops.core.config import settings


def send_slack_message(text: str) -> None:
    url = settings.slack_webhook_url
    if not url:
        return  # 운영 안정성: 없으면 조용히 스킵

    try:
        requests.post(url, json={"text": text}, timeout=3)
    except Exception:
        # 알림 실패가 시스템을 깨면 안 됨
        pass
