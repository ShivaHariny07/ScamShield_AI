from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import MessageRole, SubmissionSourceType, check_in

if TYPE_CHECKING:
    from app.models.investigation import Investigation

UNDETERMINED_LANGUAGE = "und"


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A submitted message or assistant reply within an investigation."""

    __tablename__ = "messages"
    __table_args__ = (
        check_in("role", MessageRole),
        check_in("submission_source_type", SubmissionSourceType),
        Index(
            "ix_messages_investigation_id_created_at",
            "investigation_id",
            "created_at",
        ),
    )

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("investigations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    assistant_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    # BCP-47 language tag, or "und" when undetermined.
    detected_language: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=UNDETERMINED_LANGUAGE,
        server_default=UNDETERMINED_LANGUAGE,
    )
    submission_source_type: Mapped[str] = mapped_column(String(16), nullable=False)

    investigation: Mapped[Investigation] = relationship(back_populates="messages")
