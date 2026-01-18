from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "open": {"acknowledged", "resolved"},
    "acknowledged": {"resolved", "open"},
    "resolved": {"open"},
}


def apply_status_change(row, new_status: str):
    old_status = row.status

    if new_status == old_status:
        raise HTTPException(status_code=409, detail=f"No-op transition: {old_status} → {new_status}")

    if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Invalid status transition: {old_status} → {new_status}",
        )

    now = datetime.now(timezone.utc)
    row.status = new_status

    if new_status == "acknowledged":
        row.acknowledged_at = now
        row.resolved_at = None
    elif new_status == "resolved":
        if row.acknowledged_at is None:
            row.acknowledged_at = now
        row.resolved_at = now
    elif new_status == "open":
        row.acknowledged_at = None
        row.resolved_at = None

    return row
