"""Categorical values stored as VARCHAR + CHECK constraints.

The CHECK constraints are generated from these enums, so the database and
the Python code always share one source of truth.
"""

from enum import StrEnum

from sqlalchemy import CheckConstraint


class IncidentType(StrEnum):
    SUSPICIOUS_MESSAGE_ONLY = "suspicious_message_only"
    CLICKED_LINK = "clicked_link"
    ENTERED_CREDENTIALS = "entered_credentials"
    SHARED_OTP = "shared_otp"
    TRANSFERRED_MONEY = "transferred_money"


class SubmissionType(StrEnum):
    TEXT = "text"
    SCREENSHOT = "screenshot"
    URL = "url"
    MIXED = "mixed"


class RiskCategory(StrEnum):
    # There is intentionally no "safe" value: absence of detected threats
    # never proves that content is safe.
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InvestigationStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class SubmissionSourceType(StrEnum):
    TYPED_TEXT = "typed_text"
    PASTED_TEXT = "pasted_text"
    IMAGE_OCR = "image_ocr"
    ASSISTANT = "assistant"


def check_in(column: str, enum_cls: type[StrEnum]) -> CheckConstraint:
    """Build a named CHECK constraint restricting a column to enum values.

    NULL values pass the check, so nullability is controlled by the column.
    """
    values = ", ".join(f"'{member.value}'" for member in enum_cls)
    return CheckConstraint(f"{column} IN ({values})", name=f"{column}_valid")
