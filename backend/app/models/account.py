"""The global identity: one person, one account, across every firm they work with.

Deliberately carries no firm_id — that absence is what lets a single account belong
to several firms, and it is the migration we cannot afford to do later.

Named account rather than user because `user` is a reserved word in PostgreSQL.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Identity,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Account(Base):
    __tablename__ = "account"
    __table_args__ = (
        # Unique globally, deactivated accounts included (modelo-datos 3.4):
        # reusing a deactivated person's email makes their return ambiguous.
        UniqueConstraint("email"),
        # ADR-002 asks for uniqueness over lower(email). Storing the address
        # already lowercased gives the same guarantee with a plain UNIQUE and
        # avoids an expression index, which `alembic check` reports as a diff
        # on every run.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))

    # Never the password itself. Hashing arrives with HU-1; the column exists now
    # because the first support account has to be seeded somewhere.
    password_hash: Mapped[str] = mapped_column(String(255))

    # Platform-level deactivation: this person cannot log in anywhere. Not the
    # same as firm_member.is_active, which only closes one firm's door.
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    # updated_at is kept by a database trigger, not the ORM (modelo-datos 3.11).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
