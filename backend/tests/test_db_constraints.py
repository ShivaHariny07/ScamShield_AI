"""Database-level constraint tests.

Every test runs in a rolled-back transaction (see conftest.db_session).
Expected failures run inside SAVEPOINTs (begin_nested) so the outer
transaction stays usable.
"""

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Investigation, Message, User


def make_investigation(**overrides):
    values = {"submission_type": "text"}
    values.update(overrides)
    return Investigation(**values)


def make_message(investigation_id, **overrides):
    values = {
        "investigation_id": investigation_id,
        "role": "user",
        "original_text": "Your account is blocked, share the OTP.",
        "submission_source_type": "typed_text",
    }
    values.update(overrides)
    return Message(**values)


def assert_integrity_error(session, obj):
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(obj)
            session.flush()
    session.expunge_all()


def count_investigations(session):
    return session.scalar(select(func.count()).select_from(Investigation))


def test_insert_investigation_with_messages(db_session):
    investigation = make_investigation()
    db_session.add(investigation)
    db_session.flush()
    db_session.add_all([
        make_message(investigation.id),
        make_message(
            investigation.id,
            role="assistant",
            original_text=None,
            assistant_response="This looks like an OTP scam.",
            submission_source_type="assistant",
        ),
    ])
    db_session.flush()
    db_session.expire_all()

    loaded = db_session.get(Investigation, investigation.id)
    assert isinstance(loaded.id, uuid.UUID)
    assert loaded.status == "pending"
    assert loaded.incident_type is None
    assert loaded.risk_category is None
    assert loaded.created_at.tzinfo is not None
    assert loaded.updated_at.tzinfo is not None
    assert len(loaded.messages) == 2
    for message in loaded.messages:
        assert message.detected_language == "und"
        assert message.created_at.tzinfo is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"incident_type": "phishing"},
        {"status": "done"},
        {"submission_type": "audio"},
        {"risk_category": "safe"},
    ],
)
def test_invalid_investigation_values_rejected(db_session, overrides):
    assert_integrity_error(db_session, make_investigation(**overrides))


@pytest.mark.parametrize(
    "overrides",
    [{"role": "system"}, {"submission_source_type": "email"}],
)
def test_invalid_message_values_rejected(db_session, overrides):
    investigation = make_investigation()
    db_session.add(investigation)
    db_session.flush()
    assert_integrity_error(db_session, make_message(investigation.id, **overrides))


def test_message_requires_existing_investigation(db_session):
    assert_integrity_error(db_session, make_message(uuid.uuid4()))


def test_deleting_investigation_with_messages_is_restricted(db_session):
    investigation = make_investigation()
    db_session.add(investigation)
    db_session.flush()
    db_session.add(make_message(investigation.id))
    db_session.flush()

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.delete(investigation)
            db_session.flush()


def test_deleting_user_sets_investigation_user_to_null(db_session):
    user = User()
    db_session.add(user)
    db_session.flush()
    investigation = make_investigation(user_id=user.id)
    db_session.add(investigation)
    db_session.flush()

    db_session.delete(user)
    db_session.flush()
    db_session.expire_all()

    survivor = db_session.get(Investigation, investigation.id)
    assert survivor is not None
    assert survivor.user_id is None


def test_message_with_no_text_is_accepted(db_session):
    investigation = make_investigation(submission_type="screenshot")
    db_session.add(investigation)
    db_session.flush()
    message = make_message(
        investigation.id,
        original_text=None,
        submission_source_type="image_ocr",
    )
    db_session.add(message)
    db_session.flush()
    assert message.ocr_text is None


def test_rollback_removes_inserted_records(db_session):
    # All counts use the same session/connection, so the uncommitted
    # insert is visible before rollback.
    before = count_investigations(db_session)

    db_session.add(make_investigation())
    db_session.flush()
    assert count_investigations(db_session) == before + 1

    # With join_transaction_mode="create_savepoint" this rolls back to the
    # session's savepoint; the fixture's outer transaction remains open.
    db_session.rollback()
    assert count_investigations(db_session) == before
