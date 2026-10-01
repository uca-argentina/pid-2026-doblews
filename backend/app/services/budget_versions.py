"""Saving a budget version and loading one back into the draft (HU-12).

Two operations that look symmetric and are not. Saving *copies out*: it freezes
what HU-11 computes today into rows nothing will move again. Loading *copies
back in*: it rebuilds the draft from the version's lines and lets today's prices
apply, so a version is a record of quantities, never a way to resurrect old
prices (ADR-007, consequences).

Plain functions over the session that flush and never commit, like takeoff.py,
so the route owns the transaction.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    BudgetVersion,
    BudgetVersionItem,
    BudgetVersionLine,
    Project,
    ProjectRecipe,
    Recipe,
)
from app.repositories.project_recipe import ProjectRecipeRepository
from app.services.budget import build_budget
from app.services.takeoff import TakeoffError, add_line

# What the architect reads when there is nothing to freeze. Spanish, because it
# is rendered as it is, and a constant so the tests assert this string.
EMPTY_TAKEOFF = (
    "No se puede guardar una versión con el cómputo vacío. "
    "Cargá al menos una receta y volvé a intentar."
)


class BudgetVersionError(Exception):
    """A rule refused the save. Nothing was written.

    Carries the message the architect reads, like TakeoffError does for HU-5.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True)
class LoadOutcome:
    """What loading a version actually did, which is not always all of it."""

    loaded: int
    # The recipes that were in the version and are no longer available, by name,
    # so the screen can say which lines were left out (HU-12). Names and not
    # ids: this is read by a person, not followed by a link.
    skipped: tuple[str, ...]


def _next_version_number(db: Session, project: Project) -> int:
    """The next correlative number of this work, with the race closed.

    The project row is locked first. Two saves landing together would otherwise
    both read the same MAX and both try to write it; one of them would hit
    uq_budget_version_project_id_version_number and surface as a 500 instead of
    quietly taking the next number. The lock costs nothing — the route has
    already loaded this row to resolve visibility (ADR-007 section 3).
    """
    db.execute(select(Project.id).where(Project.id == project.id).with_for_update()).scalar_one()

    return db.execute(
        select(func.coalesce(func.max(BudgetVersion.version_number), 0) + 1).where(
            BudgetVersion.project_id == project.id
        )
    ).scalar_one()


def save_version(
    db: Session,
    project: Project,
    *,
    account_id: int,
    note: str | None = None,
) -> BudgetVersion:
    """Freeze the work's budget as it stands right now.

    Takes the project rather than an id, like add_line: the route has already
    resolved it through the repository, which proved the work is this firm's,
    still active and visible to the caller.

    The numbers are not recomputed here. build_budget is the same function the
    budget screen reads, so a version holds exactly what was on screen when the
    button was pressed — if the two were computed apart they would drift, and
    nobody would notice until a client asked why.

    Both halves of ADR-007 section 2 are written here, and they are different
    kinds of copy. The items are the numbers, copied whole, resource name and
    unit included, so the version renders years later with no join at all. The
    lines are the take-off entries, one row each, keeping a live reference to
    their recipe so the version can be loaded back.
    """
    lines = ProjectRecipeRepository(db, firm_id=project.firm_id).lines(project.id)
    budget = build_budget(db, firm_id=project.firm_id, project_id=project.id)

    # The empty-take-off rule of ADR-007 section 5. prices_as_of is None only
    # when nothing priced at all, which today cannot happen with lines present —
    # every recipe has at least one resource (ADR-006). It is checked anyway,
    # and together with the lines, because a 409 saying "cargá una receta" beats
    # a NOT NULL violation surfacing as a 500 if that rule ever loosens.
    if not lines or budget.prices_as_of is None:
        raise BudgetVersionError(EMPTY_TAKEOFF)

    version = BudgetVersion(
        project_id=project.id,
        firm_id=project.firm_id,
        version_number=_next_version_number(db, project),
        note=note,
        total=budget.total,
        currency=budget.currency,
        prices_as_of=budget.prices_as_of,
        created_by=account_id,
    )
    db.add(version)
    db.flush()  # assigns the id the items and lines below hang from

    db.add_all(
        BudgetVersionItem(
            budget_version_id=version.id,
            resource_id=item.resource_id,
            resource_name=item.name,
            # From the group and not from the item: the group *is* the type, and
            # reading it here is what keeps the two from disagreeing.
            resource_type=group.type,
            unit_abbreviation=item.unit.abbreviation,
            quantity=item.quantity,
            unit_price=item.unit_price,
            currency=budget.currency,
            subtotal=item.subtotal,
        )
        for group in budget.groups
        for item in group.items
    )
    db.add_all(
        BudgetVersionLine(
            budget_version_id=version.id,
            recipe_id=line.recipe.id,
            quantity=line.quantity,
            note=line.note,
        )
        for line in lines
    )
    db.flush()

    return version


def load_version(db: Session, project: Project, version: BudgetVersion) -> LoadOutcome:
    """Replace the draft with this version's lines, at today's prices.

    Three things happen, in one transaction (ADR-007 section 5, rule 3):

    The current lines are deactivated, never deleted — the same mechanism
    remove_line uses, so nothing is lost and every read filters is_active.

    Each of the version's lines is loaded again through add_line, which is what
    decides whether a recipe may be used at all: active, and general or this
    firm's (ADR-006). Reusing it rather than re-checking here is deliberate —
    one place answers that question, and a rule added there applies to loading
    for free. A refusal is caught instead of raised: a retired recipe is not an
    error that aborts the load, it is a line left out and reported, which is
    what HU-12 asks for.

    The prices are not restored. A new take-off line always computes against the
    live reference price (ADR-005 section 5 untouched), so a version loaded
    today costs what the work would cost today. That is intentional and it is
    the single most likely thing to be read as a bug, which is why the screen
    says so.
    """
    repository = ProjectRecipeRepository(db, firm_id=project.firm_id)
    # The repository's base select already pins this firm and is_active, so this
    # is every live line of the work and nothing else.
    for current in db.scalars(
        repository.select().where(ProjectRecipe.project_id == project.id)
    ).all():
        current.is_active = False
    # Flushed before anything is added: the deactivation has to land first, or
    # the lines this call is about to create would be indistinguishable from the
    # ones it was meant to replace.
    db.flush()

    frozen = db.scalars(
        select(BudgetVersionLine)
        .where(BudgetVersionLine.budget_version_id == version.id)
        .order_by(BudgetVersionLine.id)
    ).all()

    loaded = 0
    skipped: list[str] = []
    for line in frozen:
        try:
            add_line(
                db,
                project,
                recipe_id=line.recipe_id,
                quantity=line.quantity,
                note=line.note,
            )
        except TakeoffError:
            skipped.append(_recipe_name(db, line.recipe_id))
            continue
        loaded += 1

    db.flush()
    return LoadOutcome(loaded=loaded, skipped=tuple(skipped))


def _recipe_name(db: Session, recipe_id: int) -> str:
    """The name of a recipe that could not be loaded, for the message.

    The row still exists — budget_version_line.recipe_id is a real foreign key,
    unlike an item's resource_id — so this always finds it. The fallback is
    there only so a bug in that assumption prints something readable instead of
    raising on top of an already degraded load.
    """
    name = db.execute(select(Recipe.name).where(Recipe.id == recipe_id)).scalar_one_or_none()
    return name or f"Receta #{recipe_id}"
