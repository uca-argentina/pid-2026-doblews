"""A work's take-off over HTTP (HU-5): reading it, and loading, editing and removing lines.
Where the recipe permissions guard each endpoint, a work or line out of reach becomes
a 404, and the cost is hidden from whoever may not see it.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    PROJECT_NOT_FOUND,
    CurrentAccount,
    CurrentMembership,
    DbSession,
    FirmPermissions,
    ProjectPermissions,
    requires,
    requires_any,
)
from app.models import Project, ProjectRecipe
from app.repositories.project import ProjectRepository
from app.repositories.project_recipe import ProjectRecipeRepository, TakeoffLineEntry
from app.schemas.catalog import UnitRef
from app.schemas.takeoff import (
    TakeoffLineCreate,
    TakeoffLineOut,
    TakeoffLineUpdate,
    TakeoffMaterialOut,
    TakeoffOut,
)
from app.services.authz import VIEW_ALL
from app.services.takeoff import TakeoffError, add_line, remove_line, update_line

router = APIRouter(prefix="/firms/{firm_id}/projects/{project_id}/takeoff", tags=["takeoff"])

LINE_NOT_FOUND = "Línea del cómputo no encontrada"

# HU-5 fixes the currency to ARS. The column exists on every resource so a second
# currency can arrive later, but until it does the total is a single sum.
CURRENCY = "ARS"
_ZERO = Decimal("0.00")

COST_VIEW = "project.cost.view"
MANAGE = requires("project.recipe.manage", "project")


@contextmanager
def _takeoff_rules() -> Iterator[None]:
    """Where a broken rule becomes a 409, for every write here.

    409 and not 422, as in HU-3: the body was well formed, it is the state of the
    catalogue that refuses it — the recipe was retired while the form was open.
    """
    try:
        yield
    except TakeoffError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.detail) from None


def _load_project(
    db: Session,
    membership: CurrentMembership,
    account_id: int,
    granted: frozenset[str],
    project_id: int,
) -> Project:
    """The work of the URL, or a 404.

    The guard already proved the caller holds something on this work, but not that
    the work is still active: project permissions resolve from project_member,
    which an archived work keeps. The base select of ProjectRepository filters
    is_active, so an archived work is a 404 here like on its own detail screen.
    """
    project = ProjectRepository(db, firm_id=membership.firm_id).get_visible(
        project_id, account_id, granted
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)
    return project


def _lines(db: Session, membership: CurrentMembership) -> ProjectRecipeRepository:
    """The repository, built with the firm the caller has already proved."""
    return ProjectRecipeRepository(db, firm_id=membership.firm_id)


def _load_line(
    db: Session, membership: CurrentMembership, project_id: int, line_id: int
) -> ProjectRecipe:
    """One live line of this work, or a 404. Another work's line is not this work's."""
    line = _lines(db, membership).line(project_id, line_id)
    if line is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=LINE_NOT_FOUND)
    return line


def _read_back(
    db: Session, membership: CurrentMembership, project_id: int, line_id: int
) -> TakeoffLineOut:
    """The line as stored, with its recipe's name, to answer the write that changed it.

    Raises rather than 404s: finding nothing right after a successful write is a
    bug, not a line the caller may not see.
    """
    entry: TakeoffLineEntry | None = _lines(db, membership).line_entry(project_id, line_id)
    if entry is None:
        raise RuntimeError(f"take-off line {line_id} vanished right after being written")
    return TakeoffLineOut.model_validate(entry, from_attributes=True)


@router.get(
    "",
    response_model=TakeoffOut,
    dependencies=[
        Depends(
            requires_any(
                ("project.recipe.view", "project"),
                ("project.view_all", "firm"),
            )
        )
    ],
)
def read_takeoff(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    on_project: ProjectPermissions,
    db: DbSession,
) -> TakeoffOut:
    """The whole take-off of a work: its lines, its materials and what they cost.

    Two ways in, like the work's own detail: being on the work with
    project.recipe.view, or owning the firm with project.view_all. The owner audits
    every work of their firm and has no project_member row on the ones they are
    not part of, so without the second branch they would get a 403 on the
    take-off of a work they can open.

    The cost follows the same two heights. project.cost.view is what the client
    lacks — they see what their work needs, not what it costs the firm (ADR-003
    section 8) — and project.view_all is what lets the owner see it anyway. For
    anyone else the cost fields are null, while the quantities stay.
    """
    _load_project(db, membership, account.id, granted, project_id)

    repository = _lines(db, membership)
    lines = repository.lines(project_id)
    materials = repository.materials(project_id)
    sees_cost = COST_VIEW in on_project or VIEW_ALL in granted

    return TakeoffOut(
        lines=[TakeoffLineOut.model_validate(line, from_attributes=True) for line in lines],
        materials=[
            TakeoffMaterialOut(
                resource_id=material.resource_id,
                name=material.name,
                type=material.type,
                unit=UnitRef(code=material.unit.code, abbreviation=material.unit.abbreviation),
                quantity=material.quantity,
                cost=material.cost if sees_cost else None,
                currency=material.currency,
            )
            for material in materials
        ],
        # sum() of the already rounded costs, so the column on screen adds up to
        # exactly this. The start value keeps an empty take-off at "0.00".
        total_cost=(
            sum((material.cost for material in materials), start=_ZERO) if sees_cost else None
        ),
        currency=CURRENCY,
        prices_as_of=min((material.price_updated_at for material in materials), default=None),
    )


@router.post(
    "/lines",
    response_model=TakeoffLineOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(MANAGE)],
)
def create_line(
    project_id: int,
    payload: TakeoffLineCreate,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> TakeoffLineOut:
    """Load a recipe onto the work. Only for those who may change its take-off.

    project.recipe.manage is held by lead and collaborator. The owner's
    project.view_all opens the reading and never the writing: auditing a work is
    not editing it.
    """
    project = _load_project(db, membership, account.id, granted, project_id)

    with _takeoff_rules():
        line = add_line(
            db,
            project,
            recipe_id=payload.recipe_id,
            quantity=payload.quantity,
            note=payload.note,
        )
    db.commit()

    return _read_back(db, membership, project_id, line.id)


@router.put(
    "/lines/{line_id}",
    response_model=TakeoffLineOut,
    dependencies=[Depends(MANAGE)],
)
def replace_line(
    project_id: int,
    line_id: int,
    payload: TakeoffLineUpdate,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> TakeoffLineOut:
    """Save the edit form of a line: its quantity and its note, both every time."""
    _load_project(db, membership, account.id, granted, project_id)
    line = _load_line(db, membership, project_id, line_id)

    update_line(db, line, quantity=payload.quantity, note=payload.note)
    db.commit()

    return _read_back(db, membership, project_id, line_id)


@router.delete(
    "/lines/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(MANAGE)],
)
def delete_line(
    project_id: int,
    line_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> None:
    """Remove a line. A logical deletion: its materials leave the totals at once.

    204 with no body: the screen reloads the take-off, since removing a line
    changes the totals as well as the list.
    """
    _load_project(db, membership, account.id, granted, project_id)
    line = _load_line(db, membership, project_id, line_id)

    remove_line(db, line)
    db.commit()
