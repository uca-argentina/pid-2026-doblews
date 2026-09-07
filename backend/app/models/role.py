"""The authorization catalogue: what capabilities exist and which role grants them.

Knows nothing about accounts. Seeded by migration and never written at runtime, it
is what lets a new capability be a row instead of an `if` scattered across the code.
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKeyConstraint,
    Identity,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# The three scopes, stacked widest to narrowest. VARCHAR + CHECK instead of a
# native ENUM (modelo-datos 3.7): a CHECK is changed by a reversible ALTER TABLE,
# a Postgres ENUM cannot be altered inside a transaction and breaks downgrades.
SCOPE_CHECK = "scope IN ('platform', 'firm', 'project')"


class Permission(Base):
    """One atomic capability, named resource.action."""

    __tablename__ = "permission"
    __table_args__ = (
        # Not UNIQUE(code) on its own: firm.view exists twice, granted to support
        # over any firm and to an owner over their own. Same name, different
        # capability.
        UniqueConstraint("code", "scope"),
        # Logically redundant with the primary key, and required anyway: a
        # composite foreign key can only point at a matching unique constraint.
        UniqueConstraint("id", "scope"),
        CheckConstraint(SCOPE_CHECK, name="scope_valid"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    # The only column of this table that ever appears in application code.
    code: Mapped[str] = mapped_column(String(60))
    scope: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)


class Role(Base):
    """A named bundle of permissions, with no capability of its own."""

    __tablename__ = "role"
    __table_args__ = (
        # client exists in two scopes: a firm role and a project role.
        UniqueConstraint("code", "scope"),
        # Target of the composite FK from the assignment tables, which is what
        # makes granting a project role inside a firm roster impossible.
        UniqueConstraint("id", "scope"),
        # Target of the composite FK from project_member, which also needs the
        # code in order to express its partial unique indexes.
        UniqueConstraint("id", "scope", "code"),
        CheckConstraint(SCOPE_CHECK, name="scope_valid"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    # Stable identifier, never translated and never shown raw.
    code: Mapped[str] = mapped_column(String(40))
    scope: Mapped[str] = mapped_column(String(20))
    # The label the UI actually renders. Its value stays in Spanish.
    name: Mapped[str] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)

    # Always TRUE today. It exists so that per-firm custom roles, the day they
    # are asked for, are a feature over live data rather than a migration of it.
    is_system: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class RolePermission(Base):
    """Which permissions a role grants. A missing row is the denial."""

    __tablename__ = "role_permission"
    __table_args__ = (
        # Both foreign keys read the same scope column, so a role can only be
        # wired to a permission of its own scope. That shared column is what
        # makes support + project.edit impossible to seed, with no Python
        # involved.
        ForeignKeyConstraint(
            ["role_id", "scope"],
            ["role.id", "role.scope"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["permission_id", "scope"],
            ["permission.id", "permission.scope"],
            ondelete="CASCADE",
        ),
    )

    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    permission_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    scope: Mapped[str] = mapped_column(String(20))
