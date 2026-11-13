import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    IncidentType,
    InvestigationStatus,
    RiskCategory,
    SubmissionType,
)
from app.schemas.message import MessageCreate


class InvestigationCreate(BaseModel):
    """Server-owned fields (status, risk_category, user_id, ...) are rejected."""

    model_config = ConfigDict(extra="forbid")

    submission_type: SubmissionType
    incident_type: IncidentType | None = None
    initial_message: MessageCreate | None = None


class InvestigationRead(BaseModel):
    """Public view of an investigation. user_id is intentionally omitted."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    submission_type: SubmissionType
    incident_type: IncidentType | None
    risk_category: RiskCategory | None
    status: InvestigationStatus
    progress_step: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
