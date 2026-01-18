from fastapi import FastAPI

from sentinelops.api.v1.routers.health import router as health_router
from sentinelops.api.v1.routers.stripe_webhook import router as stripe_router
from sentinelops.api.v1.routers.anomalies import router as anomalies_router
from sentinelops.core.config import settings

app = FastAPI(title="SentinelOps", version="0.1.0")
app.include_router(health_router, prefix="/api/v1")
app.include_router(stripe_router, prefix="/api/v1")
app.include_router(anomalies_router, prefix="/api/v1")

@app.on_event("startup")
def validate_settings() -> None:
    if settings.env == "local" and not settings.db_password:
        raise RuntimeError("DB_PASSWORD is missing. Check your .env file.")

