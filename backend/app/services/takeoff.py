"""The rules for loading, editing and removing the lines of a work's take-off (HU-5).
Plain functions over the session that flush and never commit, so the route owns
the transaction and turns a TakeoffError into a status code.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project, ProjectRecipe, Recipe

# What the architect reads when the recipe they picked cannot be loaded. Spanish,
# because it is rendered as it is, and a constant so the tests assert this string.
RECIPE_NOT_AVAILABLE = (
    "Esa receta ya no está disponible en el catálogo. Recargá la página y elegí otra."
)


class TakeoffError(Exception):
    """A rule refused the change. Nothing was written.

    Carries the message the architect reads, like ProjectError does for HU-3.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _check_recipe(db: Session, recipe_id: int) -> None:
    """May a new line be loaded with this recipe?

    Only while it is active. The foreign key already refuses an id that does not
    exist, but it cannot know about is_active: a recipe support retired (HU-8)
    still exists, and ADR-005 section 6 says it "deja de ofrecerse para cargar".

    Missing and retired get the same refusal because they are the same situation
    for the person at the form: the picker offered something that is no longer
    there. A missing id would otherwise surface as an IntegrityError, a 500.
    """
    is_active = db.scalar(select(Recipe.is_active).where(Recipe.id == recipe_id))
    if not is_active:
        raise TakeoffError(RECIPE_NOT_AVAILABLE)


def add_line(
    db: Session,
    project: Project,
    *,
    recipe_id: int,
    quantity: Decimal,
    note: str | None = None,
) -> ProjectRecipe:
    """Load this much of a recipe onto a work.

    Takes the project rather than an id, like update_project: the route has
    already resolved it through the repository, which is what proved the work is
    this firm's, still active, and visible to the caller.

    firm_id is copied from the project and never taken from the caller. It is the
    column the composite foreign key shares with project, so the line cannot end
    up tied to another firm's work even if a caller tried.

    No check against an existing line of the same recipe: two lines of one
    recipe are how a take-off is measured per storey (ADR-003 section 5).
    """
    _check_recipe(db, recipe_id)

    line = ProjectRecipe(
        project_id=project.id,
        firm_id=project.firm_id,
        recipe_id=recipe_id,
        quantity=quantity,
        note=note,
    )
    db.add(line)
    db.flush()  # assigns the id the route reads the line back with
    return line


def update_line(
    db: Session,
    line: ProjectRecipe,
    *,
    quantity: Decimal,
    note: str | None = None,
) -> ProjectRecipe:
    """Replace the editable state of a line: its quantity and its note.

    Both are written every time, because the form sends both: an empty note
    means the line no longer has one. The recipe is not among them. Changing it
    would change the unit the quantity is expressed in, so 120 m2 of wall would
    silently become 120 of something else; removing the line and loading a new
    one says what actually happened.
    """
    line.quantity = quantity
    line.note = note
    db.flush()
    return line


def remove_line(db: Session, line: ProjectRecipe) -> ProjectRecipe:
    """Take a line out of the take-off. A logical deletion, not a DELETE.

    Its materials leave the totals at once, because every read filters is_active
    from the base repository.
    """
    line.is_active = False
    db.flush()
    return line
