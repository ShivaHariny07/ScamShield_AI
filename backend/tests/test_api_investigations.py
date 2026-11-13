"""Investigation API tests (database required, always rolled back)."""

import uuid

import pytest
from sqlalchemy import func, select

from app.models import Investigation, Message
from app.services import messages as message_service

URL = "/api/v1/investigations"


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_create_minimal_investigation(client):
    response = client.post(URL, json={"submission_type": "text"})

    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["id"])
    assert body["status"] == "pending"
    assert body["submission_type"] == "text"
    assert body["incident_type"] is None
    assert body["risk_category"] is None
    assert "user_id" not in body


def test_create_with_incident_type(client):
    response = client.post(
        URL, json={"submission_type": "text", "incident_type": "clicked_link"}
    )
    assert response.status_code == 201
    assert response.json()["incident_type"] == "clicked_link"


def test_create_with_initial_message_stores_text_verbatim(client):
    text = "  Dear customer, your account is blocked.\nShare OTP to unblock.  "
    response = client.post(
        URL,
        json={
            "submission_type": "text",
            "initial_message": {"original_text": text},
        },
    )
    assert response.status_code == 201
    investigation_id = response.json()["id"]

    messages = client.get(f"{URL}/{investigation_id}/messages").json()
    assert len(messages) == 1
    assert messages[0]["original_text"] == text
    assert messages[0]["role"] == "user"
    assert messages[0]["submission_source_type"] == "pasted_text"
    assert messages[0]["assistant_response"] is None


def test_get_investigation(client):
    created = client.post(URL, json={"submission_type": "url"}).json()

    response = client.get(f"{URL}/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_investigation_returns_404(client):
    response = client.get(f"{URL}/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Investigation not found."}


def test_malformed_investigation_id_returns_422(client):
    assert client.get(f"{URL}/not-a-uuid").status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"submission_type": "email"},
        {"submission_type": "text", "status": "completed"},
        {"submission_type": "text", "initial_message": {"original_text": "   "}},
        {
            "submission_type": "text",
            "initial_message": {"original_text": "x", "role": "assistant"},
        },
    ],
)
def test_invalid_payload_returns_422_and_creates_nothing(client, db_session, payload):
    before = count(db_session, Investigation)
    response = client.post(URL, json=payload)
    assert response.status_code == 422
    assert count(db_session, Investigation) == before


def test_failed_initial_message_rolls_back_investigation(
    client, db_session, monkeypatch
):
    before_investigations = count(db_session, Investigation)
    before_messages = count(db_session, Message)

    def broken_message(investigation_id, data):
        # Violates the role CHECK constraint, so the commit fails.
        message = Message(
            investigation_id=investigation_id,
            role="not-a-role",
            original_text=data.original_text,
            submission_source_type=data.submission_source_type,
        )
        return message

    monkeypatch.setattr(message_service, "build_user_message", broken_message)

    response = client.post(
        URL,
        json={"submission_type": "text", "initial_message": {"original_text": "x"}},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "An internal error occurred."}
    assert count(db_session, Investigation) == before_investigations
    assert count(db_session, Message) == before_messages


def test_database_error_logs_metadata_but_not_submitted_content(
    client, monkeypatch, caplog
):
    secret = "OTP-987654 account 1234567890"

    def broken_message(investigation_id, data):
        # Violates the role CHECK constraint; PostgreSQL's error DETAIL then
        # contains the failing row, including the submitted text.
        return Message(
            investigation_id=investigation_id,
            role="not-a-role",
            original_text=data.original_text,
            submission_source_type=data.submission_source_type,
        )

    monkeypatch.setattr(message_service, "build_user_message", broken_message)

    with caplog.at_level("DEBUG"):
        response = client.post(
            URL,
            json={"submission_type": "text", "initial_message": {"original_text": secret}},
        )

    assert response.status_code == 500
    assert secret not in response.text

    # Nothing captured from any logger may contain the submitted content.
    assert secret not in caplog.text
    assert "OTP-987654" not in caplog.text
    for record in caplog.records:
        assert record.exc_info is None

    # The safe metadata is still logged for diagnosis.
    error_logs = [r.getMessage() for r in caplog.records if r.name == "app.api.errors"]
    assert error_logs == [
        "Database error during POST /api/v1/investigations: IntegrityError "
        "(sqlstate=23514, constraint=ck_messages_role_valid)"
    ]
