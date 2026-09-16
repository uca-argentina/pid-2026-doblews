"""Reading the team of one work: who is on it, and with which role (HU-6).

Not a FirmScopedRepository, for the reason repositories/member.py already gives
about its own two project_member reads: the table carries no is_active of its
own. An assignment is made inert by the roster row behind it (ADR-002 section
11.3) and never by a flag, so the base class — which refuses any model without
both firm_id and is_active — cannot scope it. The firm is pinned by hand
instead, in the one select every read here starts from, so the guarantee is the
same even though the mechanism is not.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Row, Select, select
from sqlalchemy.orm import Session

from app.models import Account, FirmMember, ProjectMember, Role

# The project role that carries responsibility for the work. Compared as a
# literal for the same reason the partial indexes on project_member do:
# role_code is the one column a rule can name without knowing the seeded ids.
LEAD = "lead"


@dataclass(frozen=True)
class TeamEntry:
    """One assignment with the labels the team section renders.

    name and email come from the global account, like a roster row: they are the
    person's identity, not something this work owns.
    """

    account_id: int
    name: str
    email: str
    role_code: str
    role_name: str
    # The state of the roster row behind the assignment, not of the assignment
    # itself. False means this person left the firm: their row is still here and
    # still theirs, it simply grants nothing until they come back (ADR-002
    # section 11.3). Showing it is what stops the lead wondering where someone
    # went, and warns them before the seat is treated as filled.
    is_active: bool
    joined_at: datetime


def _to_entry(row: Row) -> TeamEntry:
    member, name, email, role_code, role_name, roster_is_active = row
    return TeamEntry(
        account_id=member.account_id,
        name=name,
        email=email,
        role_code=role_code,
        role_name=role_name,
        is_active=roster_is_active,
        joined_at=member.joined_at,
    )


class ProjectTeamRepository:
    """Every read of one work's project_member rows starts from select()."""

    def __init__(self, db: Session, *, firm_id: int, project_id: int) -> None:
        self.db = db
        self.firm_id = firm_id
        self.project_id = project_id

    def select(self) -> Select:
        """This work's assignments, and nothing else.

        Both conditions, not just project_id. The composite foreign key against
        project (id, firm_id) already guarantees a row here belongs to a project
        of this firm, so filtering firm_id changes no result — it is what makes
        the tenant visible in the query itself rather than inferred from a
        constraint two files away.
        """
        return select(ProjectMember).where(
            ProjectMember.firm_id == self.firm_id,
            ProjectMember.project_id == self.project_id,
        )

    def _entries(self) -> Select:
        """The team with its labels, including whoever left the firm.

        The join to firm_member is an inner join and still safe: project_member
        carries a composite foreign key against firm_member (firm_id,
        account_id), so a row without its roster row cannot exist. It is here to
        read is_active, not to filter.
        """
        return (
            self.select()
            .join(Account, Account.id == ProjectMember.account_id)
            .join(Role, Role.id == ProjectMember.role_id)
            .join(
                FirmMember,
                (FirmMember.firm_id == ProjectMember.firm_id)
                & (FirmMember.account_id == ProjectMember.account_id),
            )
            .add_columns(Account.name, Account.email, Role.code, Role.name, FirmMember.is_active)
        )

    def list_team(self) -> list[TeamEntry]:
        """The team, ordered so it does not reshuffle between reloads.

        Active people first, then the lead, then by name. The lead expression
        sorts False before True in Postgres, so "is not the lead" puts the one
        who is at the top of their group — where the person reading the section
        looks first. account_id breaks ties between two people of the same name.
        """
        rows = self.db.execute(
            self._entries().order_by(
                FirmMember.is_active.desc(),
                ProjectMember.role_code != LEAD,
                Account.name,
                ProjectMember.account_id,
            )
        ).all()
        return [_to_entry(row) for row in rows]

    def entry(self, account_id: int) -> TeamEntry:
        """One assignment with its labels, to answer the write that just made it.

        Raises if the row is missing: right after a successful write that is a
        bug, not a resource the caller may not see.
        """
        return _to_entry(
            self.db.execute(self._entries().where(ProjectMember.account_id == account_id)).one()
        )

    def get(self, account_id: int) -> ProjectMember | None:
        """One assignment on this work, or None if this person is not on it.

        None covers "never assigned", "assigned to another work" and "assigned in
        another firm" alike: the endpoints answer all three with the same 404.
        Someone who left the roster is *not* None — their row is still here, and
        a lead changing or removing it is exactly how the team gets tidied up.
        """
        return self.db.scalars(self.select().where(ProjectMember.account_id == account_id)).first()

    def holder(self, role_code: str) -> ProjectMember | None:
        """Whoever holds this role on this work, or nobody.

        Only ever asked about the two roles a work has at most one of, which the
        partial unique indexes uq_project_member_lead and uq_project_member_client
        enforce — so .first() is the whole answer and not a truncation.
        """
        return self.db.scalars(self.select().where(ProjectMember.role_code == role_code)).first()
