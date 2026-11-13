"""Message API tests (database required, always rolled back)."""

import uuid

URL = "/api/v1/investigations"


def create_investigation(client):
    response = client.post(URL, json={"submission_type": "text"})
    assert response.status_code == 201
    return response.json()["id"]


def test_add_message(client):
    investigation_id = create_investigation(client)

    response = client.post(
        f"{URL}/{investigation_id}/messages",
        json={"original_text": "You won a lottery!", "submission_source_type": "typed_text"},
    )

    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["id"])
    assert body["investigation_id"] == investigation_id
    assert body["role"] == "user"
    assert body["assistant_response"] is None
    assert body["detected_language"] == "und"
    assert body["submission_source_type"] == "typed_text"


def test_add_message_with_ocr_text_and_language(client):
    investigation_id = create_investigation(client)

    response = client.post(
        f"{URL}/{investigation_id}/messages",
        json={
            "submission_source_type": "image_ocr",
            "ocr_text": "KYC update required",
            "detected_language": "en-IN",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["original_text"] is None
    assert body["ocr_text"] == "KYC update required"
    assert body["detected_language"] == "en-IN"


def test_add_message_to_unknown_investigation_returns_404(client):
    response = client.post(
        f"{URL}/{uuid.uuid4()}/messages", json={"original_text": "hello"}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Investigation not found."}


def test_client_cannot_create_assistant_messages(client):
    investigation_id = create_investigation(client)
    for payload in (
        {"original_text": "x", "role": "assistant"},
        {"original_text": "x", "assistant_response": "This message is safe."},
        {"original_text": "x", "submission_source_type": "assistant"},
    ):
        response = client.post(f"{URL}/{investigation_id}/messages", json=payload)
        assert response.status_code == 422


def test_list_messages_oldest_first(client):
    investigation_id = create_investigation(client)
    for text in ("first", "second", "third"):
        client.post(f"{URL}/{investigation_id}/messages", json={"original_text": text})

    response = client.get(f"{URL}/{investigation_id}/messages")

    assert response.status_code == 200
    # Same transaction => identical now() timestamps; ties are ordered by id,
    # so check the set and the ordering key instead of insertion order.
    messages = response.json()
    assert {m["original_text"] for m in messages} == {"first", "second", "third"}
    keys = [(m["created_at"], m["id"]) for m in messages]
    assert keys == sorted(keys)


def test_list_messages_empty(client):
    investigation_id = create_investigation(client)
    response = client.get(f"{URL}/{investigation_id}/messages")
    assert response.status_code == 200
    assert response.json() == []


def test_list_messages_unknown_investigation_returns_404(client):
    response = client.get(f"{URL}/{uuid.uuid4()}/messages")
    assert response.status_code == 404
