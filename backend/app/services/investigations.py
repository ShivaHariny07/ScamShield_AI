import uuid

from sqlalchemy.orm import Session

from app.models import Investigation
from app.schemas.investigation import InvestigationCreate
from app.services import messages as message_service
from app.services.exceptions import InvestigationNotFound


def create_investigation(db: Session, data: InvestigationCreate) -> Investigation:
    """Create an investigation and its optional first message atomically.

    Both rows are committed together or not at all.
    """
    investigation = Investigation(
        submission_type=data.submission_type.value,
        incident_type=data.incident_type.value if data.incident_type else None,
    )
    try:
        db.add(investigation)
        if data.initial_message is not None:
            db.flush()  # assigns investigation.id
            db.add(
                message_service.build_user_message(
                    investigation.id, data.initial_message
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(investigation)
    return investigation


def get_investigation(db: Session, investigation_id: uuid.UUID) -> Investigation:
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise InvestigationNotFound
    return investigation
