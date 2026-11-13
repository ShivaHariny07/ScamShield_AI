from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    IncidentType,
    InvestigationStatus,
    RiskCategory,
    SubmissionType,
    check_in,
)

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.user import User


class Investigation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One complete fraud investigation."""

    __tablename__ = "investigations"
    __table_args__ = (
        check_in("submission_type", SubmissionType),
        check_in("incident_type", IncidentType),
        check_in("risk_category", RiskCategory),
        check_in("status", InvestigationStatus),
        Index("ix_investigations_user_id", "user_id"),
        Index("ix_investigations_status", "status"),
        Index("ix_investigations_created_at", "created_at"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submission_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # Nullable: classification can happen after submission.
    incident_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Nullable: NULL means not yet assessed.
    risk_category: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=InvestigationStatus.PENDING.value,
        server_default=InvestigationStatus.PENDING.value,
    )
    progress_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Sanitized, user-safe text only. Never store internal details here.
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped[User | None] = relationship(passive_deletes=True)
    # No delete cascade: messages are evidence. The database RESTRICT blocks
    # deleting an investigation that still has messages.
    messages: Mapped[list[Message]] = relationship(
        back_populates="investigation",
        order_by="Message.created_at",
        passive_deletes="all",
    )
