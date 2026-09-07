"""Who holds which role, and where: the platform staff and each firm's roster.

Turns the catalogue into actual access. The roster row is also the gate to the
projects: if it goes inactive, that firm's project_member rows fall inert.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlatformMember(Base):
    """Product staff. Two or three rows in production, forever.

    No endpoint writes here: the first support account arrives by seed and any
    further one by migration. It is the most powerful table in the system and no
    user story asks to administer it from a screen.
    """

    __tablename__ = "platform_member"
    __table_args__ = (
        # role_scope carries no information: it is pinned to a constant so that
        # the composite FK below can only match a role whose scope is platform.
        CheckConstraint("role_scope = 'platform'", name="role_scope_fixed"),
        ForeignKeyConstraint(
            ["role_id", "role_scope"],
            ["role.id", "role.scope"],
        ),
    )

    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("account.id"), primary_key=True)
    # Inside the primary key, so one person can hold several platform roles the
    # day there is more than one.
    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_scope: Mapped[str] = mapped_column(String(20), server_default=text("'platform'"))

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FirmMember(Base):
    """The firm roster: one row per (firm, person). Multi-tenancy lives here.

    Several rows for the same person mean they belong to several firms, with a
    possibly different role in each. This row is also what project_member points
    at, so leaving the roster silently disables every project assignment there.
    """

    __tablename__ = "firm_member"
    __table_args__ = (
        CheckConstraint("role_scope = 'firm'", name="role_scope_fixed"),
        ForeignKeyConstraint(
            ["role_id", "role_scope"],
            ["role.id", "role.scope"],
        ),
        # "Which firms do I belong to?" runs on every login.
        Index("ix_firm_member_account_id", "account_id"),
    )

    firm_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("firm.id"), primary_key=True)
    account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("account.id"), primary_key=True)

    # Outside the primary key on purpose, which forces a single role per person
    # per firm: owner, architect and client are mutually exclusive, and if they
    # could stack, "a client can only be a client" would be undecidable.
    role_id: Mapped[int] = mapped_column(BigInteger)
    role_scope: Mapped[str] = mapped_column(String(20), server_default=text("'firm'"))

    # Roster-level deactivation: the person still logs in, this firm just stops
    # existing for them. Not account.is_active, which locks them out everywhere.
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
