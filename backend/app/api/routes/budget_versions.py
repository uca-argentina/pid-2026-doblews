"""A work's saved budget versions over HTTP (HU-12): saving, listing, reading and loading.

Four routes, and the list is as interesting for what it leaves out: there is no
PUT, no PATCH and no DELETE under this prefix. ADR-007 section 5, rule 2, is not
an authorization check — it is the shape of this module, and a test over the
route table is what keeps it that way.
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
    requires,
    requires_any,
)
from app.models import BudgetVersion, Project
from app.repositories.budget_version import BudgetVersionRepository
from app.repositories.project import ProjectRepository
from app.schemas.budget_version import (
    BudgetVersionCreate,
    BudgetVersionGroupOut,
    BudgetVersionItemOut,
    BudgetVersionLineOut,
    BudgetVersionLoadOut,
    BudgetVersionOut,
    BudgetVersionSummary,
)
from app.services.budget import BUDGET_GROUPS
from app.services.budget_versions import BudgetVersionError, load_version, save_version

router = APIRouter(
    prefix="/firms/{firm_id}/projects/{project_id}/budget/versions", tags=["budget-versions"]
)

VERSION_NOT_FOUND = "Versión del presupuesto no encontrada"

_ZERO = Decimal("0.00")

# Saving and loading are one capability: no role fits one without the other
# (ADR-007 section 4). Declared once, used by the two routes that write.
MANAGE = requires("project.budget.manage", "project")

# Reading a version asks exactly what reading the cost asks, and adds no
# permission of its own — which is also what keeps the client out (HU-12).
READ = requires_any(("project.cost.view", "project"), ("project.view_all", "firm"))


@contextmanager
def _version_rules() -> Iterator[None]:
    """Where a broken rule becomes a 409, for every write here.

    409 and not 422, as in HU-5: the body was well formed, it is the state of
    the work that refuses it — its last line was removed while the form was open.
    """
    try:
        yield
    except BudgetVersionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.detail) from None


def _load_project(
    db: Session,
    membership: CurrentMembership,
    account_id: int,
    granted: frozenset[str],
    project_id: int,
) -> Project:
    """The work of the URL, or a 404. Same split as HU-5 and HU-11.

    The guard already proved the caller holds something on this work; this
    proves the work is still active and theirs to see.
    """
    project = ProjectRepository(db, firm_id=membership.firm_id).get_visible(
        project_id, account_id, granted
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)
    return project


def _versions(db: Session, membership: CurrentMembership) -> BudgetVersionRepository:
    return BudgetVersionRepository(db, firm_id=membership.firm_id)


def _load_one(
    db: Session, membership: CurrentMembership, project_id: int, version_id: int
) -> BudgetVersion:
    """One version of this work, or a 404. Another work's version is not this one's."""
    version = _versions(db, membership).get(project_id, version_id)
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=VERSION_NOT_FOUND)
    return version


def _detail(db: Session, membership: CurrentMembership, version: BudgetVersion) -> BudgetVersionOut:
    """A saved version as the screen reads it: the three groups and its lines.

    The groups are rebuilt from the frozen items in the fixed order of HU-11, so
    one component renders a version and the draft. The subtotals are summed from
    the stored amounts; `total` is read from the version itself and never from
    this sum, because the stored number is the one that was agreed on.
    """
    repository = _versions(db, membership)
    items = repository.items(version.id)
    by_type = {
        group: [item for item in items if item.resource_type == group] for group in BUDGET_GROUPS
    }

    return BudgetVersionOut(
        id=version.id,
        version_number=version.version_number,
        note=version.note,
        groups=[
            BudgetVersionGroupOut(
                type=group,
                items=[
                    BudgetVersionItemOut(
                        resource_id=item.resource_id,
                        name=item.resource_name,
                        unit_abbreviation=item.unit_abbreviation,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        subtotal=item.subtotal,
                    )
                    for item in by_type[group]
                ],
                subtotal=sum((item.subtotal for item in by_type[group]), start=_ZERO),
            )
            for group in BUDGET_GROUPS
        ],
        lines=[
            BudgetVersionLineOut(
                recipe_id=line.recipe_id,
                recipe_name=line.recipe_name,
                quantity=line.quantity,
                note=line.note,
            )
            for line in repository.lines(version.id)
        ],
        total=version.total,
        currency=version.currency,
        prices_as_of=version.prices_as_of,
        created_at=version.created_at,
        created_by_name=repository.author(version),
    )


@router.post(
    "",
    response_model=BudgetVersionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(MANAGE)],
)
def create_version(
    project_id: int,
    payload: BudgetVersionCreate,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> BudgetVersionOut:
    """Freeze the budget as it stands. Only for those who may manage it.

    project.budget.manage is held by lead and collaborator. The owner's
    project.view_all opens the reading and never the writing: auditing a work is
    not deciding what gets presented to its client.
    """
    project = _load_project(db, membership, account.id, granted, project_id)

    with _version_rules():
        version = save_version(db, project, account_id=account.id, note=payload.note)
    db.commit()

    return _detail(db, membership, version)


@router.get("", response_model=list[BudgetVersionSummary], dependencies=[Depends(READ)])
def list_versions(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> list[BudgetVersionSummary]:
    """Every version of this work, newest first."""
    _load_project(db, membership, account.id, granted, project_id)

    return [
        BudgetVersionSummary.model_validate(summary, from_attributes=True)
        for summary in _versions(db, membership).summaries(project_id)
    ]


@router.get("/{version_id}", response_model=BudgetVersionOut, dependencies=[Depends(READ)])
def read_version(
    project_id: int,
    version_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> BudgetVersionOut:
    """One saved version, read-only, with the prices it was saved at."""
    _load_project(db, membership, account.id, granted, project_id)
    version = _load_one(db, membership, project_id, version_id)

    return _detail(db, membership, version)


@router.post(
    "/{version_id}/load", response_model=BudgetVersionLoadOut, dependencies=[Depends(MANAGE)]
)
def load_into_draft(
    project_id: int,
    version_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> BudgetVersionLoadOut:
    """Replace the draft's lines with this version's, at today's prices.

    A POST and not a PUT on the take-off: this is an action with a name, not a
    representation being replaced, and the answer is what the action did rather
    than what the resource now is. The version itself is untouched — it is the
    source of the copy, never its target.
    """
    project = _load_project(db, membership, account.id, granted, project_id)
    version = _load_one(db, membership, project_id, version_id)

    outcome = load_version(db, project, version)
    db.commit()

    return BudgetVersionLoadOut(loaded=outcome.loaded, skipped=list(outcome.skipped))
