"""Investigation endpoints.

SECURITY: no access control yet. Investigation UUIDs are resource
identifiers, not credentials. See docs/architecture/security-notes.md.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db, get_session_factory
from app.schemas.investigation import InvestigationCreate, InvestigationRead
from app.services import investigations as investigation_service
from app.services.exceptions import InvestigationNotFound
from app.services.processing import SessionFactory, process_investigation

router = APIRouter(prefix="/investigations", tags=["investigations"])

NOT_FOUND = "Investigation not found."


@router.post(
    "",
    response_model=InvestigationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_investigation(
    payload: InvestigationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    session_factory: SessionFactory = Depends(get_session_factory),
) -> InvestigationRead:
    investigation = investigation_service.create_investigation(db, payload)
    response = InvestigationRead.model_validate(investigation)
    if payload.initial_message is not None:
        # Only the id and a session factory cross into the background task;
        # the request session and ORM objects are never passed on.
        background_tasks.add_task(process_investigation, response.id, session_factory)
    return response


@router.get("/{investigation_id}", response_model=InvestigationRead)
def get_investigation(
    investigation_id: uuid.UUID, db: Session = Depends(get_db)
) -> InvestigationRead:
    try:
        investigation = investigation_service.get_investigation(db, investigation_id)
    except InvestigationNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from None
    return InvestigationRead.model_validate(investigation)
