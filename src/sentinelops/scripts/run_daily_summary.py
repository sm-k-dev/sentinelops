from __future__ import annotations

from datetime import datetime, timezone

from sentinelops.services.reporting.daily_summary import run_daily_ops_summary


def main() -> int:
    now = datetime.now(timezone.utc)
    result = run_daily_ops_summary(now=now)  # ✅ dict 반환

    if result.get("skipped"):
        print(f"⏭️ Daily summary skipped: {result.get('skip_reason')}")
        return 0

    print(f"✅ Daily summary delivered: {result.get('delivered')}")
    print(f"🤖 AI used: {result.get('used_ai')}")
    if result.get("ai_error"):
        print(f"AI insight error: {result.get('ai_error')}")
    if result.get("message_preview"):
        print("----- message preview -----")
        print(result["message_preview"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
