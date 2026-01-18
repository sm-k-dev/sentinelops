import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ✅ add project src/ to PYTHONPATH so "import sentinelops" works
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sentinelops.core.config import settings  # noqa: E402
from sentinelops.db.base import Base  # noqa: E402

# ✅ IMPORTANT:
# Alembic autogenerate가 metadata에 모델을 포함하려면 "모델 모듈 import"가 필요함.
# 최소한 tables를 정의한 모델들은 여기에 import해 두자.
from sentinelops.models import event  # noqa: F401, E402
from sentinelops.models import anomaly  # noqa: F401, E402
from sentinelops.models import daily_summary_delivery  # noqa: F401, E402
# daily_summary_delivery 모델이 있다면 이것도 추가
# from sentinelops.models import daily_summary_delivery  # noqa: F401, E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
