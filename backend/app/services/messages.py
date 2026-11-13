import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Investigation, Message
from app.models.enums import MessageRole
from app.schemas.message import MessageCreate
from app.services.exceptions import InvestigationNotFound


def build_user_message(investigation_id: uuid.UUID, data: MessageCreate) -> Message:
    """Build (but do not persist) a user message. Role is always "user"."""
    return Message(
        investigation_id=investigation_id,
        role=MessageRole.USER.value,
        original_text=data.original_text,
        ocr_text=data.ocr_text,
        detected_language=data.detected_language,
        submission_source_type=data.submission_source_type,
    )


def _require_investigation(db: Session, investigation_id: uuid.UUID) -> None:
    if db.get(Investigation, investigation_id) is None:
        raise InvestigationNotFound


def add_user_message(
    db: Session, investigation_id: uuid.UUID, data: MessageCreate
) -> Message:
    _require_investigation(db, investigation_id)
    message = build_user_message(investigation_id, data)
    try:
        db.add(message)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(message)
    return message


def list_messages(db: Session, investigation_id: uuid.UUID) -> list[Message]:
    """Messages of one investigation, oldest first."""
    _require_investigation(db, investigation_id)
    statement = (
        select(Message)
        .where(Message.investigation_id == investigation_id)
        .order_by(Message.created_at, Message.id)
    )
    return list(db.scalars(statement))
