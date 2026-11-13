"""Schema tests that inspect SQLAlchemy metadata only (no database needed)."""

import re

import pytest
from sqlalchemy import CheckConstraint, DateTime, String, Text, Uuid

from app.db.base import Base
from app.models import Investigation, Message, User  # noqa: F401
from app.models.enums import (
    IncidentType,
    InvestigationStatus,
    MessageRole,
    RiskCategory,
    SubmissionSourceType,
    SubmissionType,
)

TABLES = Base.metadata.tables
users = TABLES["users"]
investigations = TABLES["investigations"]
messages = TABLES["messages"]


def check_values(table, name):
    constraint = next(
        c for c in table.constraints
        if isinstance(c, CheckConstraint) and c.name == name
    )
    return set(re.findall(r"'([^']*)'", str(constraint.sqltext)))


def test_tables_registered():
    assert {"users", "investigations", "messages"} <= set(TABLES)


@pytest.mark.parametrize("table", [users, investigations, messages])
def test_uuid_primary_key_and_timestamps(table):
    pk = list(table.primary_key.columns)
    assert [c.name for c in pk] == ["id"]
    assert isinstance(pk[0].type, Uuid)
    assert "gen_random_uuid()" in str(pk[0].server_default.arg)
    for name in ("created_at", "updated_at"):
        column = table.c[name]
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True
        assert column.nullable is False
        assert column.server_default is not None
    assert table.c.updated_at.onupdate is not None


def test_users_is_minimal_placeholder():
    assert set(users.c.keys()) == {"id", "created_at", "updated_at"}


def test_investigations_columns():
    c = investigations.c
    assert c.user_id.nullable is True
    assert c.submission_type.nullable is False
    assert c.incident_type.nullable is True
    assert c.risk_category.nullable is True
    assert c.status.nullable is False
    assert c.status.server_default.arg == "pending"
    assert c.progress_step.nullable is True
    assert isinstance(c.progress_step.type, String)
    assert c.progress_step.type.length == 64
    assert c.error_message.nullable is True
    assert c.error_message.type.length == 500


def test_messages_columns():
    c = messages.c
    assert c.investigation_id.nullable is False
    assert c.role.nullable is False
    assert c.submission_source_type.nullable is False
    assert c.detected_language.nullable is False
    assert c.detected_language.server_default.arg == "und"
    for name in ("original_text", "ocr_text", "assistant_response"):
        assert isinstance(c[name].type, Text)
        assert c[name].nullable is True
    assert "evidence_id" not in c


def test_foreign_keys():
    (user_fk,) = investigations.c.user_id.foreign_keys
    assert user_fk.column is users.c.id
    assert user_fk.ondelete == "SET NULL"

    (inv_fk,) = messages.c.investigation_id.foreign_keys
    assert inv_fk.column is investigations.c.id
    assert inv_fk.ondelete == "RESTRICT"


def test_indexes():
    def index_map(table):
        return {i.name: [c.name for c in i.columns] for i in table.indexes}

    assert index_map(investigations) == {
        "ix_investigations_user_id": ["user_id"],
        "ix_investigations_status": ["status"],
        "ix_investigations_created_at": ["created_at"],
    }
    assert index_map(messages) == {
        "ix_messages_investigation_id_created_at": ["investigation_id", "created_at"],
    }


@pytest.mark.parametrize(
    ("table", "name", "enum_cls"),
    [
        (investigations, "ck_investigations_submission_type_valid", SubmissionType),
        (investigations, "ck_investigations_incident_type_valid", IncidentType),
        (investigations, "ck_investigations_risk_category_valid", RiskCategory),
        (investigations, "ck_investigations_status_valid", InvestigationStatus),
        (messages, "ck_messages_role_valid", MessageRole),
        (messages, "ck_messages_submission_source_type_valid", SubmissionSourceType),
    ],
)
def test_check_constraints_match_enums(table, name, enum_cls):
    assert check_values(table, name) == {m.value for m in enum_cls}


def test_exact_enum_values():
    assert {m.value for m in IncidentType} == {
        "suspicious_message_only",
        "clicked_link",
        "entered_credentials",
        "shared_otp",
        "transferred_money",
    }
    assert "safe" not in {m.value for m in RiskCategory}


def test_messages_has_no_text_presence_check():
    names = {c.name for c in messages.constraints if isinstance(c, CheckConstraint)}
    assert names == {
        "ck_messages_role_valid",
        "ck_messages_submission_source_type_valid",
    }
