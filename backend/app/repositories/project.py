"""Reading projects: which ones this person is allowed to see.

The first consumer of the firm-scoped base, and the place where the second level
of enforcement earns its keep. Guarding the endpoint with a permission answers
"may you list projects?"; this answers "which ones?", and no dependency can do
that for it.
"""

from sqlalchemy import Select

from app.models import Project, ProjectMember
from app.repositories.base import FirmScopedRepository

# A firm-scope permission that changes which *project* rows a read returns, which
# is exactly why the two levels of enforcement are separate. ADR-002 section 7:
# giving the owner project.view_all is what keeps "el dueño ve todas las obras de
# su estudio" a row in the seed instead of an `if is_owner` buried in here.
VIEW_ALL = "project.view_all"


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

    def list_visible(self, account_id: int, firm_permissions: frozenset[str]) -> list[Project]:
        """The project list, ordered so it does not reshuffle between reloads."""
        return list(
            self.db.scalars(self._visible(account_id, firm_permissions).order_by(Project.name))
        )

    def get_visible(
        self, project_id: int, account_id: int, firm_permissions: frozenset[str]
    ) -> Project | None:
        """One project, or None if this person may not see it.

        None covers "does not exist", "belongs to another firm", "archived" and
        "exists but you are not on it" alike, because the endpoint answers all
        four with a 404. HU-3: "Si pido por URL una obra ajena recibo 404 (no 403
        — no revelamos que existe)."
        """
        return self.db.scalars(
            self._visible(account_id, firm_permissions).where(Project.id == project_id)
        ).first()
