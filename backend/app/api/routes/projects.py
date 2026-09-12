"""The works of a firm: listing, detail, and the ABM of each one (HU-3)."""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentAccount,
    CurrentMembership,
    DbSession,
    FirmPermissions,
    requires,
    requires_any,
)
from app.models import Project
from app.repositories.project import ProjectEntry, ProjectRepository
from app.schemas.project import ProjectClientOut, ProjectOut, ProjectSummary, ProjectWrite
from app.services.project import ProjectError, archive_project, create_project, update_project

router = APIRouter(prefix="/firms/{firm_id}/projects", tags=["projects"])

PROJECT_NOT_FOUND = "Obra no encontrada"


@contextmanager
def _project_rules() -> Iterator[None]:
    """Where a broken rule becomes a status code, for every write here.

    409 Conflict and not 422: the request was well formed, it is the state of
    the firm that refuses it — the chosen client left the roster, or is not a
    client of this firm. 422 stays for what Pydantic rejects.
    """
    try:
        yield
    except ProjectError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.detail) from None


def _client_out(entry: ProjectEntry) -> ProjectClientOut | None:
    if entry.client is None:
        return None
    return ProjectClientOut(account_id=entry.client.account_id, name=entry.client.name)


def _to_summary(entry: ProjectEntry) -> ProjectSummary:
    return ProjectSummary(
        id=entry.project.id,
        name=entry.project.name,
        address=entry.project.address,
        estimated_start_date=entry.project.estimated_start_date,
        client=_client_out(entry),
    )


def _to_out(entry: ProjectEntry) -> ProjectOut:
    return ProjectOut(
        id=entry.project.id,
        name=entry.project.name,
        address=entry.project.address,
        estimated_start_date=entry.project.estimated_start_date,
        client=_client_out(entry),
        description=entry.project.description,
    )


def _projects(db: Session, membership: CurrentMembership) -> ProjectRepository:
    """The repository, built with the firm the caller has already proved.

    From the resolved membership and never from the raw path: {firm_id} is a
    string the caller chose, and get_current_membership is what turned it into
    a firm they belong to.
    """
    return ProjectRepository(db, firm_id=membership.firm_id)


def _load(
    db: Session,
    membership: CurrentMembership,
    account_id: int,
    granted: frozenset[str],
    project_id: int,
) -> Project:
    """One work this caller may act on, or a 404.

    The same 404 for "does not exist", "belongs to another firm", "archived"
    and "you are not on it", because telling them apart would confirm that
    someone else's work exists (ADR-002 section 9).

    It runs after the route's permission guard, which is not a leak: the guard
    resolves project permissions against this id, and a work of another firm
    resolves to none at all, so an outsider is refused before reaching here.
    """
    project = _projects(db, membership).get_visible(project_id, account_id, granted)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)
    return project


def _read_back(
    db: Session,
    membership: CurrentMembership,
    account_id: int,
    granted: frozenset[str],
    project_id: int,
) -> ProjectEntry:
    """The work as stored, to answer the write that just changed it.

    A read of its own rather than the model the service returned, because the
    response carries the client's name and that lives in another table. Raises
    rather than 404s when it finds nothing: right after a successful write that
    is a bug, not a resource the caller may not see.
    """
    entry = _projects(db, membership).entry(project_id, account_id, granted)
    if entry is None:
        raise RuntimeError(f"project {project_id} vanished right after being written")
    return entry


@router.get(
    "",
    response_model=list[ProjectSummary],
    dependencies=[Depends(requires("firm.view", "firm"))],
)
def list_projects(
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> list[ProjectSummary]:
    """The works of this firm that the caller may see.

    firm.view and not a project permission: there is no project_id in the path
    to resolve one against, and "may you list the works of this firm?" is a
    question about the firm. *Which* works come back is the repository's answer
    and not this permission's — ADR-002 section 8 keeps those two apart — so
    the permission set is handed along, which is what lets project.view_all
    widen the read for an owner.

    Every firm role holds firm.view, a client included: they see the works they
    were assigned to (HU-6), and an empty list until then.
    """
    entries = _projects(db, membership).list_entries(account.id, granted)
    return [_to_summary(entry) for entry in entries]


@router.post(
    "",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requires("project.create", "firm"))],
)
def create(
    payload: ProjectWrite,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> ProjectOut:
    """Create a work. The caller leads it, from the same transaction.

    project.create is firm-scope because there is no work yet to hang a project
    permission off (ADR-002 section 7). It is also what keeps a firm client out:
    they do not hold it.
    """
    with _project_rules():
        project = create_project(
            db,
            membership.firm_id,
            created_by=account.id,
            name=payload.name,
            description=payload.description,
            address=payload.address,
            estimated_start_date=payload.estimated_start_date,
            client_account_id=payload.client_account_id,
        )
    db.commit()

    return _to_out(_read_back(db, membership, account.id, granted, project.id))


@router.get(
    "/{project_id}",
    response_model=ProjectOut,
    dependencies=[
        Depends(
            requires_any(
                ("project.view", "project"),
                ("project.view_all", "firm"),
            )
        )
    ],
)
def read_project(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> ProjectOut:
    """One work in full, for its detail screen.

    Two ways in, because the right to read a work is granted at two heights:
    being on it, or owning the firm it belongs to. HU-3 promises both, and the
    owner has no project_member row for the first one to resolve from.
    """
    entry = _projects(db, membership).entry(project_id, account.id, granted)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)
    return _to_out(entry)


@router.put(
    "/{project_id}",
    response_model=ProjectOut,
    dependencies=[Depends(requires("project.edit", "project"))],
)
def replace_project(
    project_id: int,
    payload: ProjectWrite,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> ProjectOut:
    """Save the edit form: the whole editable state of the work.

    PUT and not PATCH because the form sends every field every time, so an
    empty address means the work has none rather than "leave it as it was".
    The client is part of that state and follows the same rule.
    """
    project = _load(db, membership, account.id, granted, project_id)

    with _project_rules():
        update_project(
            db,
            project,
            name=payload.name,
            description=payload.description,
            address=payload.address,
            estimated_start_date=payload.estimated_start_date,
            client_account_id=payload.client_account_id,
        )
    db.commit()

    return _to_out(_read_back(db, membership, account.id, granted, project_id))


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requires("project.archive", "project"))],
)
def archive(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> None:
    """Archive a work. A logical deletion, not a DELETE in the database.

    The verb says what happens from the API's point of view: the work is gone,
    it leaves the listing and its detail answers 404 from now on. In the
    database it is an UPDATE of project.is_active, and the team stays assigned.

    204 with no body: the frontend already has the row and only drops it.
    """
    project = _load(db, membership, account.id, granted, project_id)
    archive_project(db, project)
    db.commit()
