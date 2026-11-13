from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# hide_parameters keeps SQL parameters out of SQLAlchemy exception messages;
# app/api/errors.py additionally never logs exception text.
engine = create_engine(settings.database_url, pool_pre_ping=True, hide_parameters=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed.

    Closing a session discards anything that was not committed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
