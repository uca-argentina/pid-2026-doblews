"""Pins the rules for saving and loading a budget version, against the session and without HTTP.
The four rules ADR-007 section 5 says the schema cannot defend, plus the one thing
the whole feature exists for: that a saved version stops moving.
"""

from decimal import Decimal

import pytest
from sqlalchemy import text

from app.models import BudgetVersion, Project
from app.services.budget import build_budget
from app.services.budget_versions import (
    EMPTY_TAKEOFF,
    BudgetVersionError,
    load_version,
    save_version,
)

WALL = "Pared de ladrillo común 15cm"
SUBFLOOR = "Contrapiso de cascote"
BRICK = "Ladrillo común"

TOTAL_OF_120_M2_OF_WALL = Decimal("3877800.00")


@pytest.fixture
def project(db_session, world) -> Project:
    return db_session.get(Project, world.project_a)


@pytest.fixture
def wall(world, recipe_id, add_takeoff_line) -> int:
    """120 m2 of wall on work A, which is what most versions here freeze."""
    return add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", note="PB")


def saved(db_session, project_id: int) -> list[int]:
    return [
        row.id
        for row in db_session.execute(
            text("SELECT id FROM budget_version WHERE project_id = :p ORDER BY id"),
            {"p": project_id},
        )
    ]


def items_of(db_session, version_id: int) -> dict[str, tuple]:
    """resource name -> (type, quantity, unit price, subtotal) of the frozen items."""
    return {
        row.resource_name: (row.resource_type, row.quantity, row.unit_price, row.subtotal)
        for row in db_session.execute(
            text(
                "SELECT resource_name, resource_type, quantity, unit_price, subtotal"
                " FROM budget_version_item WHERE budget_version_id = :v"
            ),
            {"v": version_id},
        )
    }


def frozen_lines(db_session, version_id: int) -> list[tuple]:
    return [
        tuple(row)
        for row in db_session.execute(
            text(
                "SELECT quantity, note FROM budget_version_line"
                " WHERE budget_version_id = :v ORDER BY id"
            ),
            {"v": version_id},
        )
    ]


def take_off(db_session, project_id: int) -> list[tuple]:
    """(recipe_id, quantity, note, is_active) of every line, removed ones included."""
    return [
        tuple(row)
        for row in db_session.execute(
            text(
                "SELECT recipe_id, quantity, note, is_active FROM project_recipe"
                " WHERE project_id = :p ORDER BY id"
            ),
            {"p": project_id},
        )
    ]


def add_line_sql(db_session, project, recipe: int, quantity: str, note: str | None = None) -> None:
    """A take-off line written behind the service's back, as the fixtures do."""
    db_session.execute(
        text(
            "INSERT INTO project_recipe (project_id, firm_id, recipe_id, quantity, note)"
            " VALUES (:p, :f, :r, :q, :n)"
        ),
        {"p": project.id, "f": project.firm_id, "r": recipe, "q": quantity, "n": note},
    )
    db_session.flush()


def retire(db_session, recipe: int) -> None:
    """Take a recipe out of the catalogue, as HU-8's logical deletion does."""
    db_session.execute(text("UPDATE recipe SET is_active = false WHERE id = :r"), {"r": recipe})
    db_session.flush()


class TestSave:
    def test_a_version_freezes_the_budget_that_was_on_screen(
        self, db_session, project, world, wall
    ):
        """The numbers are not recomputed here: a version holds what build_budget
        said at that moment, which is what the architect was looking at. Computing
        the two apart is how they would quietly drift."""
        version = save_version(db_session, project, account_id=world.account_a)

        frozen = items_of(db_session, version.id)
        assert frozen[BRICK] == (
            "material",
            Decimal("7200.000"),
            Decimal("230.00"),
            Decimal("1656000.00"),
        )
        assert frozen["Oficial"] == (
            "labor",
            Decimal("120.000"),
            Decimal("5500.00"),
            Decimal("660000.00"),
        )
        assert version.total == TOTAL_OF_120_M2_OF_WALL
        assert version.currency == "ARS"
        assert version.prices_as_of is not None

    def test_the_frozen_subtotals_add_up_to_the_stored_total(
        self, db_session, project, world, wall
    ):
        """What makes the stored total safe to report instead of recomputing it."""
        version = save_version(db_session, project, account_id=world.account_a)

        added = sum(item[3] for item in items_of(db_session, version.id).values())
        assert added == version.total

    def test_an_item_carries_its_own_name_and_unit(self, db_session, project, world, wall):
        """Copied, not referenced: a version has to render with no join at all,
        whatever happened to the catalogue since (ADR-007 section 2)."""
        version = save_version(db_session, project, account_id=world.account_a)

        unit = db_session.execute(
            text(
                "SELECT unit_abbreviation FROM budget_version_item"
                " WHERE budget_version_id = :v AND resource_name = 'Oficial'"
            ),
            {"v": version.id},
        ).scalar_one()
        assert unit == "h"

    def test_the_take_off_lines_are_frozen_one_row_each(
        self, db_session, project, world, recipe_id
    ):
        """One row per line and not per resource: two walls measured per storey
        come back as two lines, which is what makes loading faithful."""
        add_line_sql(db_session, project, recipe_id[WALL], "70", "planta baja")
        add_line_sql(db_session, project, recipe_id[WALL], "50", "planta alta")

        version = save_version(db_session, project, account_id=world.account_a)

        # In the order the take-off itself lists them — by recipe, then by note —
        # and not in the order they were loaded. Both lines are the same wall, so
        # the note is what sorts them, and "alta" comes before "baja". Freezing
        # them in screen order is what makes a version read like the take-off it
        # came from rather than like its insertion history.
        assert frozen_lines(db_session, version.id) == [
            (Decimal("50.000"), "planta alta"),
            (Decimal("70.000"), "planta baja"),
        ]

    def test_a_work_with_no_lines_cannot_be_saved(self, db_session, project, world):
        """ADR-007 section 5, rule 1. And nothing is written on the way out."""
        with pytest.raises(BudgetVersionError) as refused:
            save_version(db_session, project, account_id=world.account_a)

        assert refused.value.detail == EMPTY_TAKEOFF
        assert saved(db_session, project.id) == []

    def test_a_work_whose_only_line_was_removed_cannot_be_saved(
        self, db_session, project, world, recipe_id, add_takeoff_line
    ):
        """A removed line is not a line: the rule reads the live take-off."""
        add_takeoff_line(project.id, world.firm_a, recipe_id[WALL], "120", is_active=False)

        with pytest.raises(BudgetVersionError):
            save_version(db_session, project, account_id=world.account_a)

    def test_the_numbering_is_correlative_within_the_work(self, db_session, project, world, wall):
        first = save_version(db_session, project, account_id=world.account_a)
        second = save_version(db_session, project, account_id=world.account_a)

        assert (first.version_number, second.version_number) == (1, 2)

    def test_each_work_numbers_from_one(
        self, db_session, world, recipe_id, add_takeoff_line, new_project, wall
    ):
        """v1 of one work and v1 of another coexist: the number is per work, not
        per platform, so one firm cannot count another's versions by its gaps."""
        other = new_project(world.firm_a, world.account_a, "Casa Segunda")
        add_takeoff_line(other, world.firm_a, recipe_id[WALL], "10")

        save_version(
            db_session, db_session.get(Project, world.project_a), account_id=world.account_a
        )
        second = save_version(
            db_session, db_session.get(Project, other), account_id=world.account_a
        )

        assert second.version_number == 1

    def test_a_blank_note_is_stored_as_no_note(self, db_session, project, world, wall):
        version = save_version(db_session, project, account_id=world.account_a, note=None)

        assert version.note is None


class TestAVersionStopsMoving:
    """Why the feature exists. ADR-005 section 5 made the price live; this is the
    artefact where it stops being, and the difference has to be visible."""

    def test_a_price_change_does_not_move_a_saved_version(self, db_session, project, world, wall):
        version = save_version(db_session, project, account_id=world.account_a)
        before = items_of(db_session, version.id)[BRICK]

        db_session.execute(
            text(
                "UPDATE resource SET reference_price = reference_price * 2,"
                " price_updated_at = now() WHERE name = :n"
            ),
            {"n": BRICK},
        )
        db_session.flush()

        assert items_of(db_session, version.id)[BRICK] == before
        assert db_session.get(BudgetVersion, version.id).total == TOTAL_OF_120_M2_OF_WALL

    def test_the_draft_does_move_while_the_version_does_not(self, db_session, project, world, wall):
        """The two showing different numbers for the same work on the same day is
        the intended consequence of freezing, not a bug (ADR-007 consequences)."""
        version = save_version(db_session, project, account_id=world.account_a)

        db_session.execute(
            text("UPDATE resource SET reference_price = reference_price * 2 WHERE name = :n"),
            {"n": BRICK},
        )
        db_session.flush()

        draft = build_budget(db_session, firm_id=project.firm_id, project_id=project.id)
        assert draft.total > db_session.get(BudgetVersion, version.id).total

    def test_editing_the_take_off_does_not_move_a_saved_version(
        self, db_session, project, world, wall, recipe_id
    ):
        version = save_version(db_session, project, account_id=world.account_a)

        add_line_sql(db_session, project, recipe_id[SUBFLOOR], "50")

        assert db_session.get(BudgetVersion, version.id).total == TOTAL_OF_120_M2_OF_WALL


class TestLoad:
    def test_loading_replaces_the_draft_with_the_versions_lines(
        self, db_session, project, world, recipe_id
    ):
        """ADR-007 section 5, rule 3. The lines that were there are deactivated
        and not deleted, so nothing is lost."""
        add_line_sql(db_session, project, recipe_id[WALL], "70", "planta baja")
        version = save_version(db_session, project, account_id=world.account_a)

        add_line_sql(db_session, project, recipe_id[SUBFLOOR], "999")

        outcome = load_version(db_session, project, version)

        assert (outcome.loaded, outcome.skipped) == (1, ())
        lines = take_off(db_session, project.id)
        # The two original rows are off, and the version's line is back as a new one.
        assert [line[3] for line in lines] == [False, False, True]
        assert lines[-1] == (recipe_id[WALL], Decimal("70.000"), "planta baja", True)

    def test_loading_recalculates_at_todays_prices(self, db_session, project, world, wall):
        """It restores the quantities, never the prices. This is the single thing
        most likely to be read as a bug, so it gets its own test."""
        version = save_version(db_session, project, account_id=world.account_a)

        db_session.execute(
            text("UPDATE resource SET reference_price = reference_price * 2 WHERE name = :n"),
            {"n": BRICK},
        )
        db_session.flush()

        load_version(db_session, project, version)

        draft = build_budget(db_session, firm_id=project.firm_id, project_id=project.id)
        assert draft.total > db_session.get(BudgetVersion, version.id).total

    def test_a_line_whose_recipe_was_retired_is_left_out_and_reported(
        self, db_session, project, world, recipe_id
    ):
        """HU-12: the screen has to say which line did not come back."""
        add_line_sql(db_session, project, recipe_id[WALL], "120")
        add_line_sql(db_session, project, recipe_id[SUBFLOOR], "50")
        version = save_version(db_session, project, account_id=world.account_a)

        retire(db_session, recipe_id[SUBFLOOR])
        outcome = load_version(db_session, project, version)

        assert outcome.loaded == 1
        assert outcome.skipped == (SUBFLOOR,)
        live = [line for line in take_off(db_session, project.id) if line[3]]
        assert [line[0] for line in live] == [recipe_id[WALL]]

    def test_loading_twice_leaves_one_copy_of_each_line(
        self, db_session, project, world, recipe_id
    ):
        """The deactivation has to land before the reload, or the second load
        would stack another copy on top of the first."""
        add_line_sql(db_session, project, recipe_id[WALL], "120")
        version = save_version(db_session, project, account_id=world.account_a)

        load_version(db_session, project, version)
        load_version(db_session, project, version)

        live = [line for line in take_off(db_session, project.id) if line[3]]
        assert len(live) == 1

    def test_the_version_itself_is_untouched_by_loading(self, db_session, project, world, wall):
        """It is the source of the copy, never its target."""
        version = save_version(db_session, project, account_id=world.account_a)
        before = items_of(db_session, version.id)

        load_version(db_session, project, version)

        assert items_of(db_session, version.id) == before
        assert db_session.get(BudgetVersion, version.id).total == TOTAL_OF_120_M2_OF_WALL

    def test_a_version_can_be_saved_again_after_loading_an_older_one(
        self, db_session, project, world, wall
    ):
        """The flow HU-12 describes: load an old version, keep working, save a
        new one. Never edit the old one."""
        first = save_version(db_session, project, account_id=world.account_a)

        load_version(db_session, project, first)
        second = save_version(db_session, project, account_id=world.account_a)

        assert second.version_number == 2
        assert saved(db_session, project.id) == [first.id, second.id]
