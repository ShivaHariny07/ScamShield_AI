"""Exception handlers that never leak database internals or submitted content.

Responses carry a generic message. Logs carry only safe metadata; the exception
text is never logged because PostgreSQL error details can include row data.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

logger = logging.getLogger("app.api.errors")

DATABASE_UNAVAILABLE = (
    "The database is temporarily unavailable. Please try again later."
)
INTERNAL_ERROR = "An internal error occurred."


def _log_database_error(label: str, request: Request, exc: SQLAlchemyError) -> None:
    """Log method, path, exception class, SQLSTATE and constraint name only."""
    original = getattr(exc, "orig", None)
    diag = getattr(original, "diag", None)
    logger.error(
        "%s during %s %s: %s (sqlstate=%s, constraint=%s)",
        label,
        request.method,
        request.url.path,
        type(exc).__name__,
        getattr(original, "sqlstate", None) or "n/a",
        getattr(diag, "constraint_name", None) or "n/a",
    )


async def database_unavailable_handler(
    request: Request, exc: OperationalError
) -> JSONResponse:
    _log_database_error("Database unavailable", request, exc)
    return JSONResponse(status_code=503, content={"detail": DATABASE_UNAVAILABLE})


async def database_error_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    _log_database_error("Database error", request, exc)
    return JSONResponse(status_code=500, content={"detail": INTERNAL_ERROR})


def register_error_handlers(app: FastAPI) -> None:
    # The more specific OperationalError is matched before SQLAlchemyError.
    app.add_exception_handler(OperationalError, database_unavailable_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
