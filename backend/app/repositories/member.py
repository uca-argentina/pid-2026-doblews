"""Reading the firm roster: who belongs to this firm, and what they hold in it.

The second consumer of the firm-scoped base, and the first one that needs the
rows the base hides by default. HU-2's listing shows each member's state, so the
people who left the roster are part of the answer, not noise to filter out.

Also answers the two questions the roster rules ask about a member's projects
before changing them. project_member has no is_active of its own (the roster row
is what makes it inert, ADR-002 section 11.3), so it cannot have a firm-scoped
repository; those reads pin firm_id by hand and live here, next to the member
they are about.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, select

from app.models import Account, FirmMember, Project, ProjectMember, Role
from app.repositories.base import FirmScopedRepository

# Project role codes, compared as literals for the same reason the partial
# indexes on project_member do: role_code is the one column a rule can name
# without knowing which ids the seed handed out.
LEAD = "lead"
CLIENT = "client"


@dataclass(frozen=True)
class RosterEntry:
    """One roster row with the labels the listing renders.

    name and email come from the global account, not from this firm: they are
    the person's identity, which is why HU-2 lets the owner change the role and
    nothing else.
    """

    account_id: int
    name: str
    email: str
    role_code: str
    role_name: str
    is_active: bool
    joined_at: datetime


class FirmMemberRepository(FirmScopedRepository[FirmMember]):
    """Every read of firm_member starts from the base select and only narrows it."""

    model = FirmMember

    def _entries(self) -> Select:
        """The roster with its labels, people who left included.

        include_inactive=True because the listing is precisely where a removed
        member stays visible: reinstating them goes through the add form (HU-2),
        and this is where the owner finds the address to type.

        Joining role on role.id alone is enough: it is the primary key, and the
        composite foreign key on firm_member already pins the scope to firm.
        """
        return (
            self.select(include_inactive=True)
            .join(Account, Account.id == FirmMember.account_id)
            .join(Role, Role.id == FirmMember.role_id)
            .add_columns(Account.name, Account.email, Role.code, Role.name)
        )

    def list_roster(self) -> list[RosterEntry]:
        """Everyone on this firm's roster: active members first, then by name.

        account_id breaks ties between two people with the same name, so the
        list does not reshuffle between reloads.
        """
        rows = self.db.execute(
            self._entries().order_by(
                FirmMember.is_active.desc(), Account.name, FirmMember.account_id
            )
        ).all()
        return [
            RosterEntry(
                account_id=member.account_id,
                name=name,
                email=email,
                role_code=role_code,
                role_name=role_name,
                is_active=member.is_active,
                joined_at=member.joined_at,
            )
            for member, name, email, role_code, role_name in rows
        ]

    def get(self, account_id: int, *, include_inactive: bool = False) -> FirmMember | None:
        """One roster row of this firm, or None.

        None covers "not on this roster", "on another firm's roster" and "does
        not exist" alike, and by default "left the roster" too: the endpoints
        answer all of them with the same 404. Adding someone is the one caller
        that asks for inactive rows, because that is how a member is reinstated.
        """
        return self.db.scalars(
            self.select(include_inactive=include_inactive).where(
                FirmMember.account_id == account_id
            )
        ).first()

    def has_non_client_project_roles(self, account_id: int) -> bool:
        """Does this person hold any project role other than client in this firm?

        What decides whether they may become a firm client: ADR-002 section 11.2
        says a firm client can only be a client on a project, and the roster
        refuses rather than touching their project roles itself.

        Archived projects count too. Archiving is a logical deletion, so the row
        is still there, and the day the project is restored its lead would come
        back as a firm client holding lead.
        """
        return bool(
            self.db.scalar(
                select(
                    select(ProjectMember.project_id)
                    .where(
                        ProjectMember.firm_id == self.firm_id,
                        ProjectMember.account_id == account_id,
                        ProjectMember.role_code != CLIENT,
                    )
                    .exists()
                )
            )
        )

    def leads_active_projects(self, account_id: int) -> bool:
        """Is this person the lead of any live project in this firm?

        What blocks removing them from the roster. Their project rows would go
        inert, but uq_project_member_lead still counts an inert row, so the
        project would be left with no working lead and no way to appoint a new
        one until they came back.

        Archived projects do not count: nobody is working on them, and the
        inert row simply waits there like any other.
        """
        return bool(
            self.db.scalar(
                select(
                    select(ProjectMember.project_id)
                    .join(Project, Project.id == ProjectMember.project_id)
                    .where(
                        ProjectMember.firm_id == self.firm_id,
                        ProjectMember.account_id == account_id,
                        ProjectMember.role_code == LEAD,
                        Project.is_active,
                    )
                    .exists()
                )
            )
        )
