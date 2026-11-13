"""Message endpoints, nested under an investigation.

SECURITY: no access control yet. Investigation UUIDs are resource
identifiers, not credentials. See docs/architecture/security-notes.md.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.message import MessageCreate, MessageRead
from app.services import messages as message_service
from app.services.exceptions import InvestigationNotFound

router = APIRouter(
    prefix="/investigations/{investigation_id}/messages", tags=["messages"]
)

NOT_FOUND = "Investigation not found."


@router.post("", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def add_message(
    investigation_id: uuid.UUID,
    payload: MessageCreate,
    db: Session = Depends(get_db),
) -> MessageRead:
    try:
        message = message_service.add_user_message(db, investigation_id, payload)
    except InvestigationNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from None
    return MessageRead.model_validate(message)


@router.get("", response_model=list[MessageRead])
def list_messages(
    investigation_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[MessageRead]:
    try:
        messages = message_service.list_messages(db, investigation_id)
    except InvestigationNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from None
    return [MessageRead.model_validate(message) for message in messages]
