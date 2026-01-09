from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from sentinelops.api.deps import db_session

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/db-ping")
def db_ping(db: Session = Depends(db_session)):  # noqa: B008
    db.execute(text("SELECT 1"))
    return {"db": "ok"}
