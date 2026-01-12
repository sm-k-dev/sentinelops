from sqlalchemy import create_engine, text
from sentinelops.core.config import settings

engine = create_engine(settings.database_url)
with engine.connect() as conn:
    rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    print("alembic_version:", rows)
