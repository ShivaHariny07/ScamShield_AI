"""Investigation endpoints.

SECURITY: no access control yet. Investigation UUIDs are resource
identifiers, not credentials. See docs/architecture/security-notes.md.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.investigation import InvestigationCreate, InvestigationRead
from app.services import investigations as investigation_service
from app.services.exceptions import InvestigationNotFound

router = APIRouter(prefix="/investigations", tags=["investigations"])

NOT_FOUND = "Investigation not found."


@router.post(
    "",
    response_model=InvestigationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_investigation(
    payload: InvestigationCreate, db: Session = Depends(get_db)
) -> InvestigationRead:
    investigation = investigation_service.create_investigation(db, payload)
    return InvestigationRead.model_validate(investigation)


@router.get("/{investigation_id}", response_model=InvestigationRead)
def get_investigation(
    investigation_id: uuid.UUID, db: Session = Depends(get_db)
) -> InvestigationRead:
    try:
        investigation = investigation_service.get_investigation(db, investigation_id)
    except InvestigationNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from None
    return InvestigationRead.model_validate(investigation)
