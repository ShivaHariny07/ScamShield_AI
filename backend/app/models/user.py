from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Placeholder table. Authentication fields are added in a later milestone."""

    __tablename__ = "users"
