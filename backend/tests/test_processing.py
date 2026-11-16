"""Background processing pipeline tests (database required, always rolled back).

process_investigation() is called directly with a session factory that
creates NEW sessions on the rolled-back test connection (see conftest).
"""

import uuid

import pytest
from sqlalchemy import update
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.models import Investigation, Message
from app.services import processing
from app.services.processing import (
    FINAL_PROGRESS_STEP,
    GENERIC_FAILURE_MESSAGE,
    ProcessingStep,
    process_investigation,
)

SECRET_TEXT = "secret OTP-123456 account 9876543210"


def make_pending(db_session, with_message=True):
    investigation = Investigation(submission_type="text")
    db_session.add(investigation)
    db_session.flush()
    if with_message:
        db_session.add(
            Message(
                investigation_id=investigation.id,
                role="user",
                original_text=SECRET_TEXT,
                submission_source_type="pasted_text",
            )
        )
    db_session.commit()
    return investigation.id


def reload(db_session, investigation_id):
    db_session.expire_all()
    return db_session.get(Investigation, investigation_id)


def set_status(session_factory, investigation_id, **values):
    """Simulate another worker/request changing the row in its own session."""
    with session_factory() as other:
        other.execute(
            update(Investigation)
            .where(Investigation.id == investigation_id)
            .values(**values)
        )
        other.commit()


def assert_no_sensitive_logs(caplog):
    assert "secret" not in caplog.text
    assert "OTP-123456" not in caplog.text
    assert "9876543210" not in caplog.text
    for record in caplog.records:
        assert record.exc_info is None


# --- success ---------------------------------------------------------------


def test_successful_processing(db_session, background_session_factory, caplog):
    investigation_id = make_pending(db_session)

    with caplog.at_level("INFO", logger="app.services.processing"):
        process_investigation(investigation_id, background_session_factory)

    investigation = reload(db_session, investigation_id)
    assert investigation.status == "completed"
    assert investigation.progress_step == FINAL_PROGRESS_STEP == "analysis_unavailable"
    assert investigation.error_message is None
    assert investigation.risk_category is None
    assert investigation.updated_at >= investigation.created_at
    assert "Processing completed" in caplog.text
    assert_no_sensitive_logs(caplog)


def test_task_uses_its_own_session(db_session, background_session_factory):
    investigation_id = make_pending(db_session)

    process_investigation(investigation_id, background_session_factory)

    assert background_session_factory.created, "task did not open a session"
    for session in background_session_factory.created:
        assert session is not db_session


def test_progress_is_visible_while_a_step_runs(
    db_session, background_session_factory, monkeypatch
):
    investigation_id = make_pending(db_session)
    observed = []

    def observe(db, inv_id):
        # Read through a different session than the task's own session.
        with background_session_factory() as other:
            row = other.get(Investigation, inv_id)
            observed.append((row.status, row.progress_step))

    monkeypatch.setattr(
        processing,
        "PROCESSING_STEPS",
        (ProcessingStep("first_step", observe), ProcessingStep("second_step", observe)),
    )

    process_investigation(investigation_id, background_session_factory)

    assert observed == [("processing", "first_step"), ("processing", "second_step")]
    assert reload(db_session, investigation_id).status == "completed"


# --- failures --------------------------------------------------------------


def test_missing_messages_fail_with_safe_message(
    db_session, background_session_factory
):
    investigation_id = make_pending(db_session, with_message=False)

    process_investigation(investigation_id, background_session_factory)

    investigation = reload(db_session, investigation_id)
    assert investigation.status == "failed"
    assert investigation.progress_step == "validating_submission"
    assert investigation.error_message == "No message content was submitted."


def test_unexpected_error_is_sanitized(
    db_session, background_session_factory, monkeypatch, caplog
):
    investigation_id = make_pending(db_session)

    def explode(db, inv_id):
        raise RuntimeError(f"boom while handling {SECRET_TEXT}")

    monkeypatch.setattr(
        processing, "PROCESSING_STEPS", (ProcessingStep("exploding_step", explode),)
    )

    with caplog.at_level("DEBUG"):
        process_investigation(investigation_id, background_session_factory)

    investigation = reload(db_session, investigation_id)
    assert investigation.status == "failed"
    assert investigation.error_message == GENERIC_FAILURE_MESSAGE
    # The step name survived the failed session's rollback, which proves the
    # progress update had been committed before the step ran.
    assert investigation.progress_step == "exploding_step"
    assert "secret" not in investigation.error_message
    assert_no_sensitive_logs(caplog)
    assert (
        f"Processing failed for investigation {investigation_id} at step "
        "exploding_step: RuntimeError (sqlstate=n/a)"
    ) in caplog.text


def test_failure_while_marking_failed_never_raises(
    db_session, background_session_factory, monkeypatch, caplog
):
    investigation_id = make_pending(db_session)
    calls = {"count": 0}

    def flaky_factory():
        calls["count"] += 1
        if calls["count"] > 1:
            raise OperationalError(
                "UPDATE investigations ...",
                {},
                Exception("connection to localhost:5433 failed: password rejected"),
            )
        return background_session_factory()

    def explode(db, inv_id):
        raise RuntimeError(SECRET_TEXT)

    monkeypatch.setattr(
        processing, "PROCESSING_STEPS", (ProcessingStep("exploding_step", explode),)
    )

    with caplog.at_level("DEBUG"):
        process_investigation(investigation_id, flaky_factory)  # must not raise

    # Could not be marked failed, so it is left "processing" (documented limitation).
    assert reload(db_session, investigation_id).status == "processing"
    assert (
        f"Could not mark investigation {investigation_id} as failed: OperationalError"
        in caplog.text
    )
    assert "localhost" not in caplog.text
    assert "password" not in caplog.text
    assert_no_sensitive_logs(caplog)


# --- stale updates never overwrite terminal states ---------------------------


@pytest.mark.parametrize(
    ("terminal_status", "terminal_error"),
    [("completed", None), ("failed", "Original failure message.")],
)
def test_stale_task_does_not_overwrite_terminal_state(
    db_session,
    background_session_factory,
    monkeypatch,
    caplog,
    terminal_status,
    terminal_error,
):
    investigation_id = make_pending(db_session)
    second_step_ran = []

    def finish_elsewhere(db, inv_id):
        set_status(
            background_session_factory,
            inv_id,
            status=terminal_status,
            progress_step="set_elsewhere",
            error_message=terminal_error,
        )

    monkeypatch.setattr(
        processing,
        "PROCESSING_STEPS",
        (
            ProcessingStep("first_step", finish_elsewhere),
            ProcessingStep("second_step", lambda db, inv_id: second_step_ran.append(1)),
        ),
    )

    with caplog.at_level("INFO", logger="app.services.processing"):
        process_investigation(investigation_id, background_session_factory)

    investigation = reload(db_session, investigation_id)
    assert investigation.status == terminal_status
    assert investigation.progress_step == "set_elsewhere"
    assert investigation.error_message == terminal_error
    assert second_step_ran == []
    assert "stale_update_skipped" in caplog.text


def test_mark_failed_does_not_overwrite_completed(
    db_session, background_session_factory, caplog
):
    investigation_id = make_pending(db_session)
    process_investigation(investigation_id, background_session_factory)

    with caplog.at_level("INFO", logger="app.services.processing"):
        processing._mark_failed(
            background_session_factory, investigation_id, "Should not be stored."
        )

    investigation = reload(db_session, investigation_id)
    assert investigation.status == "completed"
    assert investigation.error_message is None
    assert "stale_update_skipped" in caplog.text


# --- claiming --------------------------------------------------------------


@pytest.mark.parametrize("status", ["processing", "completed", "failed"])
def test_non_pending_investigation_is_not_processed(
    db_session, background_session_factory, caplog, status
):
    investigation_id = make_pending(db_session)
    set_status(
        background_session_factory,
        investigation_id,
        status=status,
        progress_step="untouched",
    )

    with caplog.at_level("INFO", logger="app.services.processing"):
        process_investigation(investigation_id, background_session_factory)

    investigation = reload(db_session, investigation_id)
    assert investigation.status == status
    assert investigation.progress_step == "untouched"
    assert "Processing skipped" in caplog.text


def test_unknown_investigation_is_skipped(background_session_factory, caplog):
    with caplog.at_level("INFO", logger="app.services.processing"):
        process_investigation(uuid.uuid4(), background_session_factory)

    assert "Processing skipped" in caplog.text


# --- delay -----------------------------------------------------------------


@pytest.mark.parametrize(("delay", "expected_sleeps"), [(0, 0), (0.01, 2)])
def test_step_delay(
    db_session, background_session_factory, monkeypatch, delay, expected_sleeps
):
    investigation_id = make_pending(db_session)
    sleeps = []
    monkeypatch.setattr(settings, "processing_step_delay_seconds", delay)
    monkeypatch.setattr(processing.time, "sleep", sleeps.append)

    process_investigation(investigation_id, background_session_factory)

    assert sleeps == [delay] * expected_sleeps
    assert reload(db_session, investigation_id).status == "completed"
