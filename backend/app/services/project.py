"""The rules for creating and changing a work (HU-3).

Plain functions over the session, like the rest of the services: they return
data and never raise HTTPException. A broken rule is a ProjectError, and turning
it into a status code is the API layer's job.

They flush and never commit. The route that calls them owns the transaction,
which is what lets "create the project" and "put its creator on it" be one
atomic act — HU-3 is explicit that if the second half does not happen, the
architect has created a work they cannot see.
"""

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import FirmMember, Project, ProjectMember, Role

# Project role codes, compared as literals for the same reason the partial
# indexes on project_member do: role_code is the one column a rule can name
# without knowing which ids the seed handed out.
LEAD = "lead"
CLIENT = "client"

# The firm role whose holders may only ever be clients on a project (ADR-002
# section 11.2). Named apart from the project role of the same code: they are
# two different roles that happen to share a word.
FIRM_CLIENT = "client"

# What the architect reads when a rule says no. Spanish, because they are
# rendered as they are, and constants so the tests assert against these very
# strings.
CLIENT_NOT_ON_ROSTER = "Esa persona no es miembro activo del estudio"
CLIENT_IS_NOT_A_CLIENT = (
    "Solo un miembro con rol de cliente puede ser el cliente de una obra. "
    "Cambiale el rol en el padrón del estudio, o elegí a otra persona."
)
FIRM_CLIENT_CANNOT_LEAD = (
    "Un cliente del estudio no puede ser responsable de una obra. "
    "Pedile a un arquitecto que la cree."
)


class ProjectError(Exception):
    """A rule refused the change. Nothing was written.

    Carries the message the architect reads, so the route passes it through
    without keeping a second table of texts.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def project_role(db: Session, code: str) -> Role:
    """The seeded project role with this code. Missing means a broken seed: a 500.

    Public, like the two helpers below it: HU-6 manages the same project_member
    rows this module writes when a work is created, and a second copy of "how do
    I turn a role code into a row" is how the two would drift apart.
    """
    return db.scalars(select(Role).where(Role.scope == "project", Role.code == code)).one()


def firm_role_code(db: Session, firm_id: int, account_id: int) -> str | None:
    """The firm role of an active member of this firm, or None if they are not one.

    One query answers both halves of every question asked below: whether the
    person is on this roster at all, and what they hold there. Resolved here
    rather than taken as an argument, so the rule cannot be defeated by a caller
    passing the wrong code.
    """
    return db.scalar(
        select(Role.code)
        .join(FirmMember, FirmMember.role_id == Role.id)
        .where(
            FirmMember.firm_id == firm_id,
            FirmMember.account_id == account_id,
            FirmMember.is_active,
        )
    )


def assign_role(db: Session, project: Project, account_id: int, code: str) -> None:
    """Put one person on a project with one role.

    Spells out firm_id and role_code because project_member needs them: the
    first is what its two composite foreign keys share, and so what ties the
    project and the person to the same firm; the second is what the partial
    unique indexes test (ADR-002 section 5).
    """
    role = project_role(db, code)
    db.add(
        ProjectMember(
            project_id=project.id,
            account_id=account_id,
            firm_id=project.firm_id,
            role_id=role.id,
            role_code=role.code,
        )
    )


def _check_client(db: Session, firm_id: int, account_id: int) -> None:
    """May this person be the client of a work of this firm?

    Two refusals, both 409s the architect can act on. Not on the roster is the
    stale-picker case: they were removed while the form was open. Not a firm
    client is the one HU-3 asks for — "el cliente se elige de un desplegable
    alimentado por el padrón filtrado por rol client" — checked here as well so
    the rule holds when the request does not come from that form.

    The inverse of this rule already lives in the roster service: HU-2 refuses
    to make someone a firm client while they hold a non-client project role
    (ADR-002 section 11.2). Together they keep the two role systems agreeing.
    """
    role_code = firm_role_code(db, firm_id, account_id)
    if role_code is None:
        raise ProjectError(CLIENT_NOT_ON_ROSTER)
    if role_code != FIRM_CLIENT:
        raise ProjectError(CLIENT_IS_NOT_A_CLIENT)


def _set_client(db: Session, project: Project, client_account_id: int | None) -> None:
    """Make this person the client of the work, or leave it with none.

    The old assignment is deleted and not deactivated. project_member has no
    is_active of its own, by design: ADR-002 section 11.3 makes an assignment
    inert through the roster row, not through a flag, so there is no logical
    deletion available here and removing someone from a work is a DELETE. The
    team rule against deleting rows is about the entities of the ABM — the
    project itself is archived, never deleted — and an assignment is not one.

    The flush between the delete and the insert is load-bearing: without it
    both statements reach the database together and uq_project_member_client,
    which allows one client row per project, refuses the pair.

    The new client is checked before the old one is removed, so a refused change
    leaves the work with the client it already had.
    """
    if client_account_id is not None:
        _check_client(db, project.firm_id, client_account_id)

    db.execute(
        delete(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.role_code == CLIENT,
        )
    )
    db.flush()

    if client_account_id is not None:
        assign_role(db, project, client_account_id, CLIENT)


def create_project(
    db: Session,
    firm_id: int,
    *,
    created_by: int,
    name: str,
    description: str | None = None,
    address: str | None = None,
    estimated_start_date: date | None = None,
    client_account_id: int | None = None,
) -> Project:
    """Create a work in this firm, with its creator leading it.

    The lead assignment is not a separate step that happens to follow. HU-3:
    "al crearla quedo asignado como lead en la misma transacción: si eso no
    pasa, creo una obra que después no puedo ver". Both rows are written here
    and the route commits once, so there is no instant in which the project
    exists without a responsible.

    Refused with ProjectError, before anything is written, when the creator is
    a firm client — they would become the lead of a work, which ADR-002 section
    11.2 forbids. In practice a firm client never reaches this, since they do
    not hold project.create; the invariant is the service's regardless, because
    that is where section 11 puts it.
    """
    if firm_role_code(db, firm_id, created_by) == FIRM_CLIENT:
        raise ProjectError(FIRM_CLIENT_CANNOT_LEAD)

    # Checked before the project row exists, so a refused client leaves nothing
    # half-written even if the caller forgets to roll back.
    if client_account_id is not None:
        _check_client(db, firm_id, client_account_id)

    project = Project(
        firm_id=firm_id,
        name=name,
        description=description,
        address=address,
        estimated_start_date=estimated_start_date,
        created_by=created_by,
    )
    db.add(project)
    db.flush()  # assigns the id both assignments need

    assign_role(db, project, created_by, LEAD)
    if client_account_id is not None:
        assign_role(db, project, client_account_id, CLIENT)

    db.flush()
    return project


def update_project(
    db: Session,
    project: Project,
    *,
    name: str,
    description: str | None = None,
    address: str | None = None,
    estimated_start_date: date | None = None,
    client_account_id: int | None = None,
) -> Project:
    """Replace the editable state of a work.

    Takes the project rather than an id: the caller has already resolved it
    through the repository, which is what proved the work is this firm's and
    that this person may see it. Looking it up again here would either repeat
    that check or, worse, skip it.

    Every field is written, including the ones left empty, because the form
    sends the whole work each time (see ProjectWrite). Neither the firm nor the
    creator is among them: a project never moves between firms (ADR-002 section
    3), and created_by is a fact about the past.
    """
    project.name = name
    project.description = description
    project.address = address
    project.estimated_start_date = estimated_start_date

    _set_client(db, project, client_account_id)

    db.flush()
    return project


def archive_project(db: Session, project: Project) -> Project:
    """Take a work out of circulation. A logical deletion, not a DELETE.

    Only project.is_active changes. The team and the client stay assigned, so
    restoring the work — which no story asks for yet — would bring back exactly
    who was on it. Nothing about the archived work is reachable afterwards: the
    firm-scoped base select filters is_active out of every read, so it leaves
    the listing and its detail answers 404 like any other work the caller may
    not see.
    """
    project.is_active = False
    db.flush()
    return project
