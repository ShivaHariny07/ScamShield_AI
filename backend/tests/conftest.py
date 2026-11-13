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
