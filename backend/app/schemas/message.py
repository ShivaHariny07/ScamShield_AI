import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import MessageRole, SubmissionSourceType

# API-level abuse guard only; the database columns are unbounded TEXT.
MAX_TEXT_LENGTH = 20_000
# BCP-47-style tag such as "en", "ta" or "en-IN"; "und" means undetermined.
LANGUAGE_TAG_PATTERN = r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$"

# Clients may only submit user content. "assistant" is written server-side only.
UserSourceType = Literal["typed_text", "pasted_text", "image_ocr"]


class MessageCreate(BaseModel):
    """A user-submitted message. The server always sets role="user"."""

    model_config = ConfigDict(extra="forbid")

    original_text: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    ocr_text: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    submission_source_type: UserSourceType = "pasted_text"
    detected_language: str = Field(
        default="und", max_length=16, pattern=LANGUAGE_TAG_PATTERN
    )

    @model_validator(mode="after")
    def require_text_for_text_sources(self) -> "MessageCreate":
        # Text is stored verbatim; blankness is only checked on a stripped copy.
        if self.submission_source_type in ("typed_text", "pasted_text"):
            if self.original_text is None or not self.original_text.strip():
                raise ValueError("Message text cannot be empty.")
        return self


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    investigation_id: uuid.UUID
    role: MessageRole
    original_text: str | None
    ocr_text: str | None
    assistant_response: str | None
    detected_language: str
    submission_source_type: SubmissionSourceType
    created_at: datetime
    updated_at: datetime
