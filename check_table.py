from sqlalchemy import create_engine, text
from sentinelops.core.config import settings

engine = create_engine(settings.database_url)
with engine.connect() as conn:
    val = conn.execute(text("SELECT to_regclass('public.daily_summary_deliveries')")).scalar()
    print("daily_summary_deliveries:", val)
