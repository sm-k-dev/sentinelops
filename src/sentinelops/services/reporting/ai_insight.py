from __future__ import annotations

from dataclasses import dataclass
import random
import re
import time
from typing import Optional, cast

from pydantic import SecretStr
from openai import OpenAI
from openai import RateLimitError, APITimeoutError, APIConnectionError

from sentinelops.core.config import settings


@dataclass(frozen=True)
class AiInsightResult:
    summary_text: Optional[str]
    model: Optional[str] = None
    error_code: Optional[str] = None     # ✅ DB에 저장할 짧은 코드
    error_detail: Optional[str] = None   # ✅ 콘솔 로그용 상세(길어질 수 있음)


_BASE_PROMPT = """You are an operations summary assistant for a billing and observability system.

Your role:
- Summarize what happened during the given time window for an operations engineer.
- Translate aggregated signals into a short, neutral operational narrative.

Strict rules:
- DO NOT compute or infer new numbers.
- DO NOT introduce causes, root analysis, or solutions.
- DO NOT give instructions, recommendations, or urgency.
- DO NOT exaggerate risk or certainty.

Style:
- Calm, factual, observational.
- Prefer phrases like "was observed", "remained stable", "appears".

Output constraints:
- 3 to 5 sentences.
- One short paragraph.
- No bullet points, no titles, no markdown.

Return ONLY the summary text.
"""

_TONE_LOW = """Tone adjustment (LOW):
- Treat signals as informational.
- Use calm, lightweight language.
- Emphasize stability and normal ranges.
- Avoid risk-focused wording.
"""

_TONE_MEDIUM = """Tone adjustment (MEDIUM):
- Acknowledge noticeable patterns without alarm.
- Use balanced language suggesting it is worth monitoring.
- Avoid urgency or directives.
"""

_TONE_HIGH = """Tone adjustment (HIGH):
- Clearly state that high-severity signals were observed.
- Keep a composed, factual tone.
- Do not soften the presence of critical signals, but do not add urgency.
- Focus on clarity over reassurance.
"""

_BANNED_PATTERNS = [
    r"\bmust\b",
    r"\bshould\b",
    r"\bimmediately\b",
    r"\burgent\b",
    r"\bguarantee\b",
    r"\bfix\b",
    r"\btake action\b",
    r"\brecommend\b",
    r"\byou need to\b",
    r"\bwe need to\b",
]

_MAX_CHARS = 650


def _sanitize(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"\n{3,}", "\n\n", t)

    for pat in _BANNED_PATTERNS:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)

    t = re.sub(r"[ \t]{2,}", " ", t).strip()

    if len(t) > _MAX_CHARS:
        t = t[:_MAX_CHARS].rstrip()
        if not t.endswith((".", "!", "?")):
            t += "…"

    return t


def _pick_tone_block(max_severity: str) -> str:
    sev = (max_severity or "low").lower()
    if sev == "high":
        return _TONE_HIGH
    if sev == "medium":
        return _TONE_MEDIUM
    return _TONE_LOW


def _call_openai_once(*, api_key: str, model: str, prompt: str, timeout_sec: int) -> str:
    client = OpenAI(api_key=api_key)
    resp = client.responses.create(
        model=model,
        input=prompt,
        timeout=timeout_sec,
    )
    return resp.output_text or ""


def _call_openai_with_retry(*, api_key: str, model: str, prompt: str, timeout_sec: int) -> str:
    max_attempts = 3
    base_delay = 1.5

    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return _call_openai_once(api_key=api_key, model=model, prompt=prompt, timeout_sec=timeout_sec)
        except (RateLimitError, APITimeoutError, APIConnectionError) as e:
            last_err = e
            if attempt == max_attempts:
                break
            sleep_s = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.6)
            time.sleep(sleep_s)

    assert last_err is not None
    raise last_err


def generate_ai_insight(ai_payload: dict) -> AiInsightResult:
    key_obj = getattr(settings, "openai_api_key", None)
    model_obj = getattr(settings, "ai_summary_model", None)

    if not key_obj or not model_obj:
        return AiInsightResult(summary_text=None, model=None, error_code="ai_not_configured", error_detail=None)

    key_obj = cast(SecretStr, key_obj)
    model = cast(str, model_obj)

    api_key: str = key_obj.get_secret_value()
    timeout_sec: int = int(getattr(settings, "ai_summary_timeout_sec", 12))

    max_sev = str(ai_payload.get("max_severity", "low"))
    tone_block = _pick_tone_block(max_sev)

    prompt = (
        _BASE_PROMPT
        + "\n"
        + tone_block
        + "\n"
        + "Aggregated operational snapshot:\n"
        + repr(ai_payload)
    )

    try:
        raw = _call_openai_with_retry(api_key=api_key, model=model, prompt=prompt, timeout_sec=timeout_sec)
        cleaned = _sanitize(raw)
        if not cleaned:
            return AiInsightResult(summary_text=None, model=model, error_code="ai_empty", error_detail=None)
        return AiInsightResult(summary_text=cleaned, model=model, error_code=None, error_detail=None)

    except RateLimitError as e:
        return AiInsightResult(summary_text=None, model=model, error_code="ai_rate_limited", error_detail=str(e))

    except Exception as e:
        return AiInsightResult(summary_text=None, model=model, error_code=f"ai_failed:{type(e).__name__}", error_detail=str(e))
