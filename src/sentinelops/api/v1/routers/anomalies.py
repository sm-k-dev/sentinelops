from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from sentinelops.core.anomaly_status import ANOMALY_STATUSES
from sentinelops.db.session import get_db
from sentinelops.models.anomaly import Anomaly
from sentinelops.services.anomaly_lifecycle import apply_status_change
from sentinelops.services.reporting.anomalies_query import list_anomalies

from sentinelops.api.v1.schemas.anomaly import (
    AnomalyListOut,
    AnomalyOut,
    AnomalyStatusUpdateIn,
)

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("", response_model=AnomalyListOut)
def get_anomalies(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(default=None, description="open/acknowledged/resolved"),
    only_open: bool = Query(default=False),
    demo_only: bool = Query(default=False, description="Filter demo anomalies only"),
    sort: str = Query(default="recent", pattern="^(recent|severity_desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
):
    if status is not None and status not in ANOMALY_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status: {status}")

    rows = list_anomalies(
        db,
        status=status,
        only_open=only_open,
        sort=sort,
        limit=limit,
        demo_only=demo_only,
    )
    items = [AnomalyOut.model_validate(r) for r in rows]
    return AnomalyListOut(items=items, count=len(items))


@router.get("/open", response_model=AnomalyListOut)
def get_open_anomalies_sorted_by_severity(
    db: Session = Depends(get_db),
    demo_only: bool = Query(default=False, description="Filter demo anomalies only"),
    limit: int = Query(default=50, ge=1, le=200),
):
    rows = list_anomalies(
        db,
        only_open=True,
        demo_only=demo_only,
        sort="severity_desc",
        limit=limit,
    )
    items = [AnomalyOut.model_validate(r) for r in rows]
    return AnomalyListOut(items=items, count=len(items))


@router.get("/{anomaly_id}", response_model=AnomalyOut)
def get_anomaly_by_id(anomaly_id: int, db: Session = Depends(get_db)):
    row = db.get(Anomaly, anomaly_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return AnomalyOut.model_validate(row)


@router.patch("/{anomaly_id}", response_model=AnomalyOut)
def update_anomaly_status(
    anomaly_id: int,
    payload: AnomalyStatusUpdateIn,
    db: Session = Depends(get_db),
):
    new_status = payload.status
    if new_status not in ANOMALY_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status: {new_status}")

    row = db.get(Anomaly, anomaly_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    apply_status_change(row, new_status)
    db.commit()
    db.refresh(row)
    return AnomalyOut.model_validate(row)


@router.post("/{anomaly_id}/ack", response_model=AnomalyOut)
def ack_anomaly(anomaly_id: int, db: Session = Depends(get_db)):
    row = db.get(Anomaly, anomaly_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    apply_status_change(row, "acknowledged")
    db.commit()
    db.refresh(row)
    return AnomalyOut.model_validate(row)


@router.post("/{anomaly_id}/resolve", response_model=AnomalyOut)
def resolve_anomaly(anomaly_id: int, db: Session = Depends(get_db)):
    row = db.get(Anomaly, anomaly_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    apply_status_change(row, "resolved")
    db.commit()
    db.refresh(row)
    return AnomalyOut.model_validate(row)
