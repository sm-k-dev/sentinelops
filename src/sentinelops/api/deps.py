from collections.abc import Generator

from sqlalchemy.orm import Session

from sentinelops.db.session import get_db


def db_session() -> Generator[Session, None, None]:
    """FastAPI dependency: DB session"""
    yield from get_db()