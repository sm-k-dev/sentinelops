from sqlalchemy import create_engine, text
from sentinelops.core.config import settings

TARGET = "214644219862"  # 이전 revision

engine = create_engine(settings.database_url)
with engine.connect() as conn:
    conn.execute(text("UPDATE alembic_version SET version_num=:v"), {"v": TARGET})
    conn.commit()
    print("alembic_version forced to", TARGET)
