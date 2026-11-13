"""Shared fixtures.

Database tests run inside an outer transaction that is always rolled back,
so they never leave records behind. They are skipped (with a reason shown by
`pytest -rs`) if the database is unreachable or the migration is not applied.
"""

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

REQUIRED_TABLES = {"users", "investigations", "messages"}


@pytest.fixture(scope="session")
def db_engine():
    try:
        from app.db.session import engine

        with engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
    except Exception as exc:  # noqa: BLE001 - any failure means "skip"
        # Only the exception type is shown; never connection details.
        pytest.skip(f"Database unreachable: {type(exc).__name__}")

    missing = REQUIRED_TABLES - tables
    if missing:
        pytest.skip(
            f"Migrations not applied (missing tables: {', '.join(sorted(missing))})"
        )
    return engine


@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """API client whose requests all use the rolled-back test session.

    Service-level commit() only releases a SAVEPOINT, so nothing persists.
    """
    from fastapi.testclient import TestClient

    from app.db.session import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
