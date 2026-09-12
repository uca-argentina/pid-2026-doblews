"""Reading projects: which ones this person is allowed to see, and with whom.

The first consumer of the firm-scoped base, and the place where the second level
of enforcement earns its keep. Guarding the endpoint with a permission answers
"may you list projects?"; this answers "which ones?", and no dependency can do
that for it.

It also answers "who is the client of each one", because HU-3's listing shows
the client and ADR-002 section 6 is explicit that there is no project.client_id
to read it from: the client is a row of project_member, so finding it is a join
and belongs here rather than in a second query per listed project.
"""

from dataclasses import dataclass

from sqlalchemy import Select
from sqlalchemy.orm import aliased

from app.models import Account, FirmMember, Project, ProjectMember
from app.repositories.base import FirmScopedRepository

# A firm-scope permission that changes which *project* rows a read returns, which
# is exactly why the two levels of enforcement are separate. ADR-002 section 7:
# giving the owner project.view_all is what keeps "el dueño ve todas las obras de
# su estudio" a row in the seed instead of an `if is_owner` buried in here.
VIEW_ALL = "project.view_all"

# The project role that makes someone the client of a work. Compared as a literal
# for the same reason the partial index uq_project_member_client does it:
# role_code is the one column a rule can name without knowing the seeded ids.
CLIENT = "client"


@dataclass(frozen=True)
class ProjectClient:
    """The client of a project, as the listing renders them."""

    account_id: int
    name: str


@dataclass(frozen=True)
class ProjectEntry:
    """One project together with its client, which may be nobody.

    Holds the Project itself rather than copying its columns out: unlike a
    roster row, the project *is* the answer here and the client is the label
    beside it. Flattening would restate the model for nothing.
    """

    project: Project
    client: ProjectClient | None


class ProjectRepository(FirmScopedRepository[Project]):
    """Every read of project starts from the base select and only narrows it."""

    model = Project

    def _visible(self, account_id: int, firm_permissions: frozenset[str]) -> Select:
        """This firm's live projects, narrowed to the ones this person may see.

        Takes the already-resolved permission set rather than looking it up: the
        request holds it, and re-querying would mean the same answer fetched
        twice for one call.

        Without project.view_all the join to project_member is what implements
        HU-3's "solo veo las obras del estudio activo donde soy miembro". The
        join needs no firm_id of its own: project_member's composite foreign key
        against project (id, firm_id) already guarantees any row it finds belongs
        to a project of this firm, and the base select has pinned that firm.
        """
        statement = self.select()
        if VIEW_ALL in firm_permissions:
            return statement
        return statement.join(ProjectMember, ProjectMember.project_id == Project.id).where(
            ProjectMember.account_id == account_id
        )

    def _with_client(self, account_id: int, firm_permissions: frozenset[str]) -> Select:
        """The visible projects, each with its client's name when it has one.

        Three outer joins and not one, chained so that a project with no client
        still comes back: the first finds the client's assignment, the second
        their name, the third their roster row.

        That third one is the load-bearing join. A client who left the firm
        keeps their project_member row, inert (ADR-002 section 11.3), so without
        checking the roster the listing would keep printing the name of someone
        who is no longer reachable in this firm. Inactive roster, no client
        shown — and the row is still there for the day they come back.

        project_member is aliased because _visible() may already have joined it
        to answer "which projects"; that one is about the *caller*, this one
        about the client, and they are almost never the same row.

        Neither join can multiply the result. project_member's primary key is
        (project_id, account_id), so the caller's join matches at most once, and
        uq_project_member_client makes the client's match at most once too.
        """
        assignment = aliased(ProjectMember)
        return (
            self._visible(account_id, firm_permissions)
            .outerjoin(
                assignment,
                (assignment.project_id == Project.id) & (assignment.role_code == CLIENT),
            )
            .outerjoin(Account, Account.id == assignment.account_id)
            .outerjoin(
                FirmMember,
                (FirmMember.firm_id == assignment.firm_id)
                & (FirmMember.account_id == assignment.account_id)
                & FirmMember.is_active,
            )
            .add_columns(
                # From the roster row and not from the assignment: that is what
                # makes an inert client read as no client at all.
                FirmMember.account_id.label("client_account_id"),
                Account.name.label("client_name"),
            )
        )

    def list_entries(self, account_id: int, firm_permissions: frozenset[str]) -> list[ProjectEntry]:
        """The project listing, ordered so it does not reshuffle between reloads.

        id breaks ties between two works of the same name, which is allowed:
        nothing makes a project name unique within a firm, and a studio really
        can have two "Casa Rodríguez".
        """
        rows = self.db.execute(
            self._with_client(account_id, firm_permissions).order_by(Project.name, Project.id)
        ).all()
        return [_to_entry(row) for row in rows]

    def entry(
        self, project_id: int, account_id: int, firm_permissions: frozenset[str]
    ) -> ProjectEntry | None:
        """One project with its client, or None if this person may not see it.

        Same None as get_visible below, for the same four reasons.
        """
        row = self.db.execute(
            self._with_client(account_id, firm_permissions).where(Project.id == project_id)
        ).first()
        return None if row is None else _to_entry(row)

    def get_visible(
        self, project_id: int, account_id: int, firm_permissions: frozenset[str]
    ) -> Project | None:
        """One project, or None if this person may not see it.

        None covers "does not exist", "belongs to another firm", "archived" and
        "exists but you are not on it" alike, because the endpoint answers all
        four with a 404. HU-3: "Si pido por URL una obra ajena recibo 404 (no 403
        — no revelamos que existe)."

        Returns the model and not an entry, because its callers are the writes:
        they need the row to change it, and the client's name is not part of
        deciding whether they may.
        """
        return self.db.scalars(
            self._visible(account_id, firm_permissions).where(Project.id == project_id)
        ).first()


def _to_entry(row) -> ProjectEntry:
    project, client_account_id, client_name = row
    return ProjectEntry(
        project=project,
        client=(
            None
            if client_account_id is None
            else ProjectClient(account_id=client_account_id, name=client_name)
        ),
    )
