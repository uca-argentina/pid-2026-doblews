"""Reading a work's saved budget versions (HU-12).

Not a FirmScopedRepository, for the same reason ProjectTeamRepository is not:
the base class refuses any model without both firm_id and is_active, and a
version carries no is_active — it is never deactivated, because it is never
anything but what it was (ADR-007 section 1). The firm is pinned by hand
instead, in the one select every read here starts from, so the guarantee is the
same even though the mechanism is not.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    BudgetVersion,
    BudgetVersionItem,
    BudgetVersionLine,
    ProjectRecipe,
    Recipe,
)


@dataclass(frozen=True)
class VersionSummary:
    """One row of the listing: enough to choose a version, not to read it."""

    id: int
    version_number: int
    note: str | None
    total: Decimal
    currency: str
    created_at: datetime
    created_by_name: str
    # Whether loading this version would leave the take-off as it is today.
    matches_takeoff: bool


@dataclass(frozen=True)
class VersionLineEntry:
    """One take-off line of a version, with its recipe's name read live.

    The name is not frozen alongside the line: the reference is real and a
    renamed recipe is still the same recipe. The item is where nothing is read
    live — that is the half meant to survive the catalogue.
    """

    recipe_id: int
    recipe_name: str
    quantity: Decimal
    note: str | None


class BudgetVersionRepository:
    """Every read starts from the base select, so it is this firm's rows only."""

    def __init__(self, db: Session, firm_id: int) -> None:
        self.db = db
        self.firm_id = firm_id

    def select(self) -> Select:
        """This firm's versions, and nothing else. No is_active: there is none."""
        return select(BudgetVersion).where(BudgetVersion.firm_id == self.firm_id)

    def first(self, project_id: int) -> BudgetVersion | None:
        """The work's v1, or None while it has no saved budget.

        What the dashboard calls the original budget (HU-19, D-17): the first
        one frozen, usually the one presented. Versions are never removed
        (ADR-007), so the first stays the first.
        """
        return self.db.scalars(
            self.select()
            .where(BudgetVersion.project_id == project_id)
            .order_by(BudgetVersion.version_number)
            .limit(1)
        ).first()

    def summaries(self, project_id: int) -> list[VersionSummary]:
        """The versions of one work, newest first.

        By version_number and not by created_at: the number is what the screen
        shows and what a person says out loud ("la v3"), and two versions saved
        in the same second would otherwise order arbitrarily.
        """
        rows = self.db.execute(
            self.select()
            .where(BudgetVersion.project_id == project_id)
            .join(Account, Account.id == BudgetVersion.created_by)
            .add_columns(Account.name)
            .order_by(BudgetVersion.version_number.desc())
        ).all()
        matching = self.matching_takeoff(project_id)
        return [
            VersionSummary(
                id=version.id,
                version_number=version.version_number,
                note=version.note,
                total=version.total,
                currency=version.currency,
                created_at=version.created_at,
                created_by_name=author,
                matches_takeoff=version.id in matching,
            )
            for version, author in rows
        ]

    def matching_takeoff(self, project_id: int) -> frozenset[int]:
        """The ids of the versions whose lines are the work's take-off of today.

        This is how the listing says which saved budget the work is standing on.
        It is computed and not stored: a "last loaded version" column would go
        on naming a version after the take-off was edited away from it, and
        would say nothing of a version that was just saved from this very
        take-off. Comparing answers the question as asked, every time.

        A line is its recipe, its quantity and its note, which is everything a
        version freezes about one and everything loading it brings back. Lines
        are counted and not just collected, because two lines of the same
        recipe with the same quantity and note are two lines. Prices are not
        part of it: the same quantities at a different price are still the same
        take-off, with a different total.

        More than one version can match — saving twice without touching
        anything gives two — and none does while there are unsaved changes.
        """
        current = Counter(
            self.db.execute(
                select(ProjectRecipe.recipe_id, ProjectRecipe.quantity, ProjectRecipe.note).where(
                    ProjectRecipe.firm_id == self.firm_id,
                    ProjectRecipe.project_id == project_id,
                    ProjectRecipe.is_active,
                )
            ).tuples()
        )
        if not current:
            # An empty take-off matches nothing: a version always has lines.
            return frozenset()

        frozen: dict[int, Counter] = defaultdict(Counter)
        for version_id, recipe_id, quantity, note in self.db.execute(
            select(
                BudgetVersionLine.budget_version_id,
                BudgetVersionLine.recipe_id,
                BudgetVersionLine.quantity,
                BudgetVersionLine.note,
            )
            .join(BudgetVersion, BudgetVersion.id == BudgetVersionLine.budget_version_id)
            .where(
                BudgetVersion.firm_id == self.firm_id,
                BudgetVersion.project_id == project_id,
            )
        ):
            frozen[version_id][(recipe_id, quantity, note)] += 1

        return frozenset(version_id for version_id, lines in frozen.items() if lines == current)

    def get(self, project_id: int, version_id: int) -> BudgetVersion | None:
        """One version of this work, or None.

        None covers "does not exist", "belongs to another work" and "belongs to
        another firm" alike, which the route turns into one 404. Asking for the
        project_id as well as the version's own id is what stops work A's URL
        from showing a version of work B of the same firm.
        """
        return self.db.scalars(
            self.select().where(
                BudgetVersion.project_id == project_id, BudgetVersion.id == version_id
            )
        ).first()

    def author(self, version: BudgetVersion) -> str:
        """Who saved it. A separate read because the detail fetches one row."""
        return self.db.execute(
            select(Account.name).where(Account.id == version.created_by)
        ).scalar_one()

    def items(self, version_id: int) -> list[BudgetVersionItem]:
        """The frozen numbers, ordered as the screen groups them.

        By name inside the group, which is the order the draft already uses, so
        a version and the budget it came from read the same way.
        """
        return list(
            self.db.scalars(
                select(BudgetVersionItem)
                .where(BudgetVersionItem.budget_version_id == version_id)
                .order_by(BudgetVersionItem.resource_name, BudgetVersionItem.id)
            ).all()
        )

    def lines(self, version_id: int) -> list[VersionLineEntry]:
        """The take-off lines of a version, with their recipes' current names."""
        rows = self.db.execute(
            select(
                BudgetVersionLine.recipe_id,
                Recipe.name,
                BudgetVersionLine.quantity,
                BudgetVersionLine.note,
            )
            .join(Recipe, Recipe.id == BudgetVersionLine.recipe_id)
            .where(BudgetVersionLine.budget_version_id == version_id)
            .order_by(Recipe.name, BudgetVersionLine.note, BudgetVersionLine.id)
        ).all()
        return [
            VersionLineEntry(recipe_id=recipe_id, recipe_name=name, quantity=quantity, note=note)
            for recipe_id, name, quantity, note in rows
        ]
