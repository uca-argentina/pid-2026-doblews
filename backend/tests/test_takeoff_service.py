"""Pins the rules for writing a work's take-off, against the session and without HTTP.
The status codes these rules become are the API tests' business; here it is what
gets written, and that a refused change writes nothing.
"""

from decimal import Decimal

import pytest
from sqlalchemy import text

from app.models import Project, ProjectRecipe
from app.services.takeoff import (
    RECIPE_NOT_AVAILABLE,
    TakeoffError,
    add_line,
    remove_line,
    update_line,
)

WALL = "Pared de ladrillo común 15cm"


def lines_in(db_session, project_id: int) -> list[tuple]:
    """(recipe_id, quantity, note, is_active) of every row, removed ones included."""
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


@pytest.fixture
def project(db_session, world) -> Project:
    return db_session.get(Project, world.project_a)


class TestAdd:
    def test_a_line_is_loaded_onto_the_work(self, db_session, project, recipe_id):
        line = add_line(
            db_session, project, recipe_id=recipe_id[WALL], quantity=Decimal("120"), note="PB"
        )

        assert line.id is not None
        assert lines_in(db_session, project.id) == [(recipe_id[WALL], Decimal("120"), "PB", True)]

    def test_the_line_takes_the_firm_of_its_work(self, db_session, project, world, recipe_id):
        line = add_line(db_session, project, recipe_id=recipe_id[WALL], quantity=Decimal("1"))

        assert line.firm_id == world.firm_a

    def test_the_same_recipe_can_be_loaded_twice(self, db_session, project, recipe_id):
        """ADR-003 section 5: no UNIQUE (project_id, recipe_id), on purpose."""
        add_line(db_session, project, recipe_id=recipe_id[WALL], quantity=Decimal("70"))
        add_line(db_session, project, recipe_id=recipe_id[WALL], quantity=Decimal("50"))

        assert len(lines_in(db_session, project.id)) == 2

    def test_a_retired_recipe_is_refused_and_nothing_is_written(
        self, db, db_session, project, recipe_id
    ):
        db.execute(
            text("UPDATE recipe SET is_active = false WHERE id = :r"), {"r": recipe_id[WALL]}
        )

        with pytest.raises(TakeoffError) as refused:
            add_line(db_session, project, recipe_id=recipe_id[WALL], quantity=Decimal("120"))

        assert refused.value.detail == RECIPE_NOT_AVAILABLE
        assert lines_in(db_session, project.id) == []

    def test_a_recipe_that_does_not_exist_gets_the_same_refusal(self, db_session, project):
        """Not an IntegrityError from the foreign key, which would be a 500."""
        with pytest.raises(TakeoffError) as refused:
            add_line(db_session, project, recipe_id=999_999, quantity=Decimal("120"))

        assert refused.value.detail == RECIPE_NOT_AVAILABLE
        assert lines_in(db_session, project.id) == []


class TestUpdate:
    @pytest.fixture
    def line(self, db_session, world, recipe_id, add_takeoff_line) -> ProjectRecipe:
        line_id = add_takeoff_line(
            world.project_a, world.firm_a, recipe_id[WALL], "120", note="planta baja"
        )
        return db_session.get(ProjectRecipe, line_id)

    def test_the_quantity_and_note_are_replaced(self, db_session, line, recipe_id):
        update_line(db_session, line, quantity=Decimal("80.5"), note="planta alta")

        assert lines_in(db_session, line.project_id) == [
            (recipe_id[WALL], Decimal("80.5"), "planta alta", True)
        ]

    def test_leaving_the_note_out_clears_it(self, db_session, line):
        """The form sends the whole line: no note means the line has none."""
        update_line(db_session, line, quantity=Decimal("120"))

        assert lines_in(db_session, line.project_id)[0][2] is None


class TestRemove:
    def test_the_line_is_deactivated_not_deleted(
        self, db_session, world, recipe_id, add_takeoff_line
    ):
        line_id = add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")
        line = db_session.get(ProjectRecipe, line_id)

        remove_line(db_session, line)

        assert lines_in(db_session, world.project_a) == [
            (recipe_id[WALL], Decimal("120"), None, False)
        ]
