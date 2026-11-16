"""Background investigation processing pipeline (FastAPI BackgroundTasks).

Rules enforced here:
- The task receives only an investigation id and a session factory. It never
  receives or reuses the request-scoped Session or any ORM object.
- Processing starts only by atomically claiming a "pending" investigation.
- Every later write is guarded by status == "processing", so a stale task can
  never overwrite a terminal state ("completed" or "failed").
- Failures store a fixed, user-safe message. Logs carry metadata only: never
  exception text, tracebacks or submitted message content.

No real analysis exists yet. Later milestones append steps (OCR, URL
scanning, LLM analysis) to PROCESSING_STEPS.
"""

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Investigation, Message
from app.models.enums import InvestigationStatus

logger = logging.getLogger("app.services.processing")

SessionFactory = Callable[[], Session]

# Final progress step on success: processing ran, but no analysis exists yet,
# so the investigation has NOT been assessed (risk_category stays NULL).
FINAL_PROGRESS_STEP = "analysis_unavailable"
GENERIC_FAILURE_MESSAGE = (
    "Processing failed due to an internal error. Please try again later."
)
MAX_ERROR_MESSAGE_LENGTH = 500


class ProcessingError(Exception):
    """An expected processing failure carrying a fixed, user-safe message."""

    def __init__(self, safe_message: str) -> None:
        super().__init__(safe_message)
        self.safe_message = safe_message


class _StaleUpdate(Exception):
    """The investigation is no longer "processing"; stop without writing."""


@dataclass(frozen=True)
class ProcessingStep:
    name: str
    run: Callable[[Session, uuid.UUID], None]


def _validate_submission(db: Session, investigation_id: uuid.UUID) -> None:
    message_count = db.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.investigation_id == investigation_id)
    )
    if not message_count:
        raise ProcessingError("No message content was submitted.")


def _prepare_analysis(db: Session, investigation_id: uuid.UUID) -> None:
    """Placeholder: OCR, URL scanning and LLM steps will be added later."""


PROCESSING_STEPS: tuple[ProcessingStep, ...] = (
    ProcessingStep("validating_submission", _validate_submission),
    ProcessingStep("preparing_analysis", _prepare_analysis),
)


def _claim(db: Session, investigation_id: uuid.UUID, first_step: str) -> bool:
    """Atomically move pending -> processing. False if not pending or missing."""
    result = db.execute(
        update(Investigation)
        .where(
            Investigation.id == investigation_id,
            Investigation.status == InvestigationStatus.PENDING.value,
        )
        .values(
            status=InvestigationStatus.PROCESSING.value,
            progress_step=first_step,
            error_message=None,
        )
    )
    db.commit()
    return result.rowcount == 1


def _update_if_processing(
    db: Session, investigation_id: uuid.UUID, **values: object
) -> bool:
    """Apply values only while the investigation is still "processing"."""
    result = db.execute(
        update(Investigation)
        .where(
            Investigation.id == investigation_id,
            Investigation.status == InvestigationStatus.PROCESSING.value,
        )
        .values(**values)
    )
    db.commit()
    return result.rowcount == 1


def _set_step(db: Session, investigation_id: uuid.UUID, step: str) -> None:
    if not _update_if_processing(db, investigation_id, progress_step=step):
        raise _StaleUpdate


def _complete(db: Session, investigation_id: uuid.UUID) -> None:
    if not _update_if_processing(
        db,
        investigation_id,
        status=InvestigationStatus.COMPLETED.value,
        progress_step=FINAL_PROGRESS_STEP,
    ):
        raise _StaleUpdate


def _mark_failed(
    session_factory: SessionFactory, investigation_id: uuid.UUID, safe_message: str
) -> None:
    """Mark as failed in a fresh session. Never overwrites a terminal state."""
    try:
        with session_factory() as db:
            updated = _update_if_processing(
                db,
                investigation_id,
                status=InvestigationStatus.FAILED.value,
                error_message=safe_message[:MAX_ERROR_MESSAGE_LENGTH],
            )
    except Exception as exc:  # noqa: BLE001 - must never escape the task
        logger.error(
            "Could not mark investigation %s as failed: %s",
            investigation_id,
            type(exc).__name__,
        )
        return
    if not updated:
        logger.warning(
            "stale_update_skipped: investigation %s was not marked failed "
            "because it is no longer processing",
            investigation_id,
        )


def _sqlstate(exc: Exception) -> str:
    return getattr(getattr(exc, "orig", None), "sqlstate", None) or "n/a"


def _pause_between_steps() -> None:
    delay = settings.processing_step_delay_seconds
    if delay > 0:
        time.sleep(delay)


def process_investigation(
    investigation_id: uuid.UUID, session_factory: SessionFactory
) -> None:
    """Run the pipeline for one investigation. Never raises."""
    current_step: str | None = None
    steps = PROCESSING_STEPS
    try:
        with session_factory() as db:
            first_step = steps[0].name if steps else FINAL_PROGRESS_STEP
            if not _claim(db, investigation_id, first_step):
                logger.info(
                    "Processing skipped for investigation %s: not pending or not found",
                    investigation_id,
                )
                return

            logger.info("Processing started for investigation %s", investigation_id)
            for step in steps:
                current_step = step.name
                _set_step(db, investigation_id, step.name)
                _pause_between_steps()
                step.run(db, investigation_id)

            current_step = FINAL_PROGRESS_STEP
            _complete(db, investigation_id)
        logger.info("Processing completed for investigation %s", investigation_id)
    except _StaleUpdate:
        logger.warning(
            "stale_update_skipped: investigation %s is no longer processing "
            "(step=%s); pipeline stopped without writing",
            investigation_id,
            current_step or "n/a",
        )
    except Exception as exc:  # noqa: BLE001 - must never escape the task
        # Exiting the "with" block closed the session, rolling back any
        # uncommitted work. Only metadata is logged.
        logger.error(
            "Processing failed for investigation %s at step %s: %s (sqlstate=%s)",
            investigation_id,
            current_step or "n/a",
            type(exc).__name__,
            _sqlstate(exc),
        )
        safe_message = (
            exc.safe_message
            if isinstance(exc, ProcessingError)
            else GENERIC_FAILURE_MESSAGE
        )
        _mark_failed(session_factory, investigation_id, safe_message)
