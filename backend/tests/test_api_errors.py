"""Error handlers must not leak database internals (no database needed)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.db.session import get_db
from app.main import app

LEAK_MARKERS = ("psycopg", "sqlalchemy", "select", "insert", "localhost", "5433", "password")


@pytest.fixture
def failing_client():
    """Yields a function that makes get_db raise the given exception."""

    def use(exc):
        def broken_db():
            raise exc
            yield  # pragma: no cover - makes this a generator dependency

        app.dependency_overrides[get_db] = broken_db
        return TestClient(app, raise_server_exceptions=False)

    try:
        yield use
    finally:
        app.dependency_overrides.pop(get_db, None)


def assert_no_leak(response):
    body = response.text.lower()
    for marker in LEAK_MARKERS:
        assert marker not in body, f"response leaked {marker!r}"


def test_operational_error_returns_503(failing_client):
    exc = OperationalError(
        "SELECT secret FROM investigations",
        {},
        Exception("connection to localhost:5433 failed: password authentication"),
    )
    response = failing_client(exc).post(
        "/api/v1/investigations", json={"submission_type": "text"}
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "The database is temporarily unavailable. Please try again later."
    }
    assert_no_leak(response)


def test_generic_database_error_returns_500(failing_client):
    exc = SQLAlchemyError("INSERT INTO messages failed on psycopg connection")
    response = failing_client(exc).get(
        "/api/v1/investigations/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "An internal error occurred."}
    assert_no_leak(response)


def test_health_still_works():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
