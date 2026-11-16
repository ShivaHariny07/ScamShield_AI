"""API + background task tests (database required, always rolled back).

Starlette's TestClient runs background tasks before client.post() returns,
so the task has finished when the next statement runs.

All test requests share one request session (see conftest). It caches loaded
rows, so tests call db_session.expire_all() before reading the results of
background work. In production each request gets a fresh session.
"""

from app.models import Message
from app.services import messages as message_service
from app.services import processing
from app.services.processing import GENERIC_FAILURE_MESSAGE, ProcessingStep

URL = "/api/v1/investigations"
SECRET_TEXT = "Your OTP is 445566. Send it to 9123456789 now."


def create(client, **payload):
    body = {"submission_type": "text", **payload}
    return client.post(URL, json=body)


def get_fresh(client, db_session, investigation_id):
    db_session.expire_all()
    response = client.get(f"{URL}/{investigation_id}")
    assert response.status_code == 200
    return response.json()


def test_post_returns_pending_then_background_completes(
    client, db_session, background_session_factory
):
    response = create(client, initial_message={"original_text": SECRET_TEXT})

    assert response.status_code == 201
    body = response.json()
    # The response is built before the background task runs.
    assert body["status"] == "pending"
    assert body["progress_step"] is None

    latest = get_fresh(client, db_session, body["id"])
    assert latest["status"] == "completed"
    assert latest["progress_step"] == "analysis_unavailable"
    assert latest["risk_category"] is None
    assert latest["error_message"] is None

    # Background work used its own session(s), never the request session.
    assert background_session_factory.created
    assert all(s is not db_session for s in background_session_factory.created)


def test_post_without_initial_message_is_not_processed(
    client, db_session, background_session_factory
):
    response = create(client)
    assert response.status_code == 201

    latest = get_fresh(client, db_session, response.json()["id"])
    assert latest["status"] == "pending"
    assert latest["progress_step"] is None
    assert background_session_factory.created == []


def test_background_failure_is_reported_safely(
    client, db_session, monkeypatch, caplog
):
    def explode(db, investigation_id):
        raise RuntimeError(f"internal failure near {SECRET_TEXT}")

    monkeypatch.setattr(
        processing, "PROCESSING_STEPS", (ProcessingStep("exploding_step", explode),)
    )

    with caplog.at_level("DEBUG"):
        response = create(client, initial_message={"original_text": SECRET_TEXT})

    assert response.status_code == 201
    assert response.json()["status"] == "pending"

    latest = get_fresh(client, db_session, response.json()["id"])
    assert latest["status"] == "failed"
    assert latest["progress_step"] == "exploding_step"
    assert latest["error_message"] == GENERIC_FAILURE_MESSAGE

    for text in (response.text, str(latest), caplog.text):
        assert "445566" not in text
        assert "9123456789" not in text
        assert "internal failure" not in text
    for record in caplog.records:
        assert record.exc_info is None


def test_validation_error_schedules_no_task(client, background_session_factory):
    response = create(client, initial_message={"original_text": "   "})
    assert response.status_code == 422
    assert background_session_factory.created == []


def test_creation_failure_schedules_no_task(
    client, monkeypatch, background_session_factory
):
    def broken_message(investigation_id, data):
        return Message(
            investigation_id=investigation_id,
            role="not-a-role",  # violates the CHECK constraint
            original_text=data.original_text,
            submission_source_type=data.submission_source_type,
        )

    monkeypatch.setattr(message_service, "build_user_message", broken_message)

    response = create(client, initial_message={"original_text": "x"})
    assert response.status_code == 500
    assert background_session_factory.created == []


def test_messages_api_unchanged_by_processing(client, db_session):
    response = create(client, initial_message={"original_text": SECRET_TEXT})
    investigation_id = response.json()["id"]

    messages = client.get(f"{URL}/{investigation_id}/messages").json()
    assert len(messages) == 1
    assert messages[0]["original_text"] == SECRET_TEXT
    assert messages[0]["assistant_response"] is None
