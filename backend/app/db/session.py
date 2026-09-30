"""Database connectivity: the process-wide engine and its session factory.

Owns how the backend reaches Postgres so nothing else builds engines or connections,
and hands FastAPI one short-lived Session per request through get_db().
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# One engine per process. It owns the connection pool, so building a second one
# doubles the connections held against Postgres without buying anything.
engine = create_engine(
    settings.database_url,
    # Managed Postgres (Azure) drops idle connections. Without this, the first
    # request after a quiet period fails instead of getting a fresh connection.
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    # Emit SQL only when we ask to, so a constraint violation surfaces at the
    # flush we wrote and not in the middle of an unrelated query.
    autoflush=False,
    # Keep attributes readable after commit: FastAPI serializes the response
    # once the session is already closed.
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding one Session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
