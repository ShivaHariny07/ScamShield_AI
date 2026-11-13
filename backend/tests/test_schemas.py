"""Pydantic request schema validation (no database needed)."""

import pytest
from pydantic import ValidationError

from app.schemas.investigation import InvestigationCreate
from app.schemas.message import MAX_TEXT_LENGTH, MessageCreate


def test_valid_message_defaults():
    message = MessageCreate(original_text="Share your OTP now")
    assert message.submission_source_type == "pasted_text"
    assert message.detected_language == "und"
    assert message.ocr_text is None


def test_message_text_is_kept_verbatim():
    text = "  Your KYC expired!\n Click here  "
    assert MessageCreate(original_text=text).original_text == text


@pytest.mark.parametrize("language", ["en", "ta", "en-IN", "und", "zh-Hant-TW"])
def test_valid_language_tags(language):
    assert MessageCreate(original_text="x", detected_language=language)


@pytest.mark.parametrize("language", ["", "english", "en_IN", "e", "en-", "1en"])
def test_invalid_language_tags_rejected(language):
    with pytest.raises(ValidationError):
        MessageCreate(original_text="x", detected_language=language)


@pytest.mark.parametrize("source", ["typed_text", "pasted_text"])
@pytest.mark.parametrize("text", [None, "", "   ", "\n\t"])
def test_text_sources_require_non_blank_text(source, text):
    with pytest.raises(ValidationError, match="Message text cannot be empty"):
        MessageCreate(original_text=text, submission_source_type=source)


def test_image_ocr_allows_no_text():
    message = MessageCreate(submission_source_type="image_ocr")
    assert message.original_text is None
    assert message.ocr_text is None


def test_assistant_source_rejected():
    with pytest.raises(ValidationError):
        MessageCreate(original_text="x", submission_source_type="assistant")


@pytest.mark.parametrize(
    "extra",
    [
        {"role": "assistant"},
        {"assistant_response": "This is safe"},
        {"investigation_id": "00000000-0000-0000-0000-000000000000"},
    ],
)
def test_message_server_owned_fields_rejected(extra):
    with pytest.raises(ValidationError):
        MessageCreate(original_text="x", **extra)


@pytest.mark.parametrize("field", ["original_text", "ocr_text"])
def test_text_length_limit(field):
    MessageCreate(**{field: "a" * MAX_TEXT_LENGTH, "submission_source_type": "image_ocr"})
    with pytest.raises(ValidationError):
        MessageCreate(
            **{field: "a" * (MAX_TEXT_LENGTH + 1), "submission_source_type": "image_ocr"}
        )


def test_investigation_minimal_payload():
    investigation = InvestigationCreate(submission_type="text")
    assert investigation.incident_type is None
    assert investigation.initial_message is None


def test_investigation_with_initial_message():
    investigation = InvestigationCreate(
        submission_type="text",
        incident_type="shared_otp",
        initial_message={"original_text": "Send OTP"},
    )
    assert investigation.initial_message.original_text == "Send OTP"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"submission_type": "email"},
        {"submission_type": "text", "incident_type": "phishing"},
        {"submission_type": "text", "initial_message": {"original_text": " "}},
    ],
)
def test_invalid_investigation_payloads(payload):
    with pytest.raises(ValidationError):
        InvestigationCreate(**payload)


@pytest.mark.parametrize(
    "extra",
    [
        {"status": "completed"},
        {"risk_category": "low"},
        {"user_id": "00000000-0000-0000-0000-000000000000"},
        {"id": "00000000-0000-0000-0000-000000000000"},
        {"error_message": "x"},
    ],
)
def test_investigation_server_owned_fields_rejected(extra):
    with pytest.raises(ValidationError):
        InvestigationCreate(submission_type="text", **extra)
