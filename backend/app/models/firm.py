"""The tenant: one architecture firm, and the boundary all its data lives inside.

Every business table carries a firm_id pointing here and every read filters by it,
so this is the anchor that keeps one firm's data invisible to the others.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Firm(Base):
    __tablename__ = "firm"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    name: Mapped[str] = mapped_column(String(120))
    contact_email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))

    # Suspension by platform support (HU-7): a suspended firm lets nobody in,
    # and nothing is deleted.
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    # updated_at is kept by a database trigger, not the ORM (modelo-datos 3.11).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
