"""Pins what a work's take-off reads back: which lines, and what materials they add up to.
The numbers come from the seeded catalogue, so ADR-003's promise of 7,200 bricks
and 30 bags for 120 m2 of wall is checked against the real yields and prices.
"""

from decimal import Decimal

import pytest
from sqlalchemy import text

from app.repositories.project_recipe import ProjectRecipeRepository

WALL = "Pared de ladrillo común 15cm"
SUBFLOOR = "Contrapiso de cascote"
SCREED = "Carpeta de cemento"

BRICK = "Ladrillo común"
CEMENT = "Cemento portland (bolsa 50 kg)"


def repo(db_session, firm_id: int) -> ProjectRecipeRepository:
    return ProjectRecipeRepository(db_session, firm_id=firm_id)


def retire(db, recipe: int) -> None:
    """Take a recipe out of the catalogue, as HU-8's logical deletion will."""
    db.execute(text("UPDATE recipe SET is_active = false WHERE id = :r"), {"r": recipe})


def by_name(materials) -> dict[str, tuple[Decimal, Decimal]]:
    """material name -> (quantity, cost), which is what most assertions compare."""
    return {material.name: (material.quantity, material.cost) for material in materials}


class TestMaterials:
    def test_the_wall_of_adr_003_computes_its_bricks_and_cement(
        self, db_session, world, recipe_id, add_takeoff_line
    ):
        """ADR-003, Consecuencias: 120 m2 of wall need 7,200 bricks and 30 bags.

        The other two materials are there too: the seeded wall also takes lime
        and sand, and a take-off that dropped them would be cheaper than the wall.
        So are T-06's hours, 1 h/m2 of each trade: the query does not filter by
        type, and grouping them apart is HU-11's job, not this repository's.
        """
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")

        found = by_name(repo(db_session, world.firm_a).materials(world.project_a))

        assert found == {
            BRICK: (Decimal("7200"), Decimal("1656000.00")),
            CEMENT: (Decimal("30"), Decimal("480000.00")),
            "Cal hidratada (bolsa 25 kg)": (Decimal("24"), Decimal("276000.00")),
            "Arena gruesa": (Decimal("5.64"), Decimal("253800.00")),
            "Oficial": (Decimal("120"), Decimal("660000.00")),
            "Ayudante": (Decimal("120"), Decimal("552000.00")),
        }

    def test_two_lines_of_the_same_recipe_add_up(
        self, db_session, world, recipe_id, add_takeoff_line
    ):
        """HU-5: measuring the wall per storey is normal, and the quantities add."""
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "70", note="planta baja")
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "50", note="planta alta")

        found = by_name(repo(db_session, world.firm_a).materials(world.project_a))

        assert found[BRICK] == (Decimal("7200"), Decimal("1656000.00"))

    def test_two_recipes_sharing_a_material_land_on_one_row(
        self, db_session, world, recipe_id, add_takeoff_line
    ):
        """Wall and subfloor both take cement: one row of 30 + 15 bags, not two rows."""
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[SUBFLOOR], "50")

        materials = repo(db_session, world.firm_a).materials(world.project_a)

        assert [material.name for material in materials].count(CEMENT) == 1
        assert by_name(materials)[CEMENT] == (Decimal("45"), Decimal("720000.00"))

    def test_quantities_are_rounded_to_three_decimals_and_costs_to_two(
        self, db_session, world, recipe_id, add_takeoff_line
    ):
        """33.333 m2 of screed x 0.025 m3 of fine sand is 0.833325 m3, which no
        one buys. Its cost, 39,999.60, is rounded from the unrounded quantity."""
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[SCREED], "33.333")

        found = by_name(repo(db_session, world.firm_a).materials(world.project_a))

        assert found["Arena fina"] == (Decimal("0.833"), Decimal("39999.60"))

    def test_the_materials_carry_their_currency_and_price_date(
        self, db_session, world, recipe_id, add_takeoff_line
    ):
        """What the screen needs for "precios de referencia al <fecha>" (ADR-005 5)."""
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "1")

        materials = repo(db_session, world.firm_a).materials(world.project_a)

        assert {material.currency for material in materials} == {"ARS"}
        assert all(material.price_updated_at is not None for material in materials)

    def test_a_removed_line_does_not_count(self, db_session, world, recipe_id, add_takeoff_line):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "500", is_active=False)

        found = by_name(repo(db_session, world.firm_a).materials(world.project_a))

        assert found[BRICK][0] == Decimal("7200")

    def test_a_retired_recipe_keeps_counting(
        self, db, db_session, world, recipe_id, add_takeoff_line
    ):
        """ADR-005 section 6: retiring a recipe must not change the budget of the
        works that already use it."""
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")
        retire(db, recipe_id[WALL])

        found = by_name(repo(db_session, world.firm_a).materials(world.project_a))

        assert found[BRICK][0] == Decimal("7200")

    def test_an_empty_take_off_is_an_empty_list(self, db_session, world):
        assert repo(db_session, world.firm_a).materials(world.project_a) == []


class TestLines:
    def test_a_line_comes_back_with_its_recipe(
        self, db_session, world, recipe_id, add_takeoff_line
    ):
        line_id = add_takeoff_line(
            world.project_a, world.firm_a, recipe_id[WALL], "120", note="planta baja"
        )

        (line,) = repo(db_session, world.firm_a).lines(world.project_a)

        assert line.id == line_id
        assert (line.recipe.id, line.recipe.name) == (recipe_id[WALL], WALL)
        assert line.recipe.unit.code == "m2"
        assert (line.quantity, line.note) == (Decimal("120"), "planta baja")

    def test_lines_are_ordered_by_recipe_then_note(
        self, db_session, world, recipe_id, add_takeoff_line
    ):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "50", note="planta baja")
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[SUBFLOOR], "30")
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "70", note="planta alta")

        lines = repo(db_session, world.firm_a).lines(world.project_a)

        assert [(line.recipe.name, line.note) for line in lines] == [
            (SUBFLOOR, None),
            (WALL, "planta alta"),
            (WALL, "planta baja"),
        ]

    def test_a_removed_line_is_not_listed(self, db_session, world, recipe_id, add_takeoff_line):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", is_active=False)

        assert repo(db_session, world.firm_a).lines(world.project_a) == []

    def test_a_retired_recipe_is_still_listed(
        self, db, db_session, world, recipe_id, add_takeoff_line
    ):
        """Its materials still count, so the line that explains them stays."""
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")
        retire(db, recipe_id[WALL])

        assert len(repo(db_session, world.firm_a).lines(world.project_a)) == 1


class TestLineTask:
    """HU-13: each line of the take-off shows which task it is assigned to."""

    def test_an_assigned_line_carries_its_task(
        self, db_session, world, recipe_id, add_takeoff_line, add_task
    ):
        task = add_task(world.project_a, world.firm_a, "Mampostería")
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", task=task)

        (line,) = repo(db_session, world.firm_a).lines(world.project_a)

        assert (line.task.id, line.task.name) == (task, "Mampostería")

    def test_an_unassigned_line_has_no_task(self, db_session, world, recipe_id, add_takeoff_line):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")

        (line,) = repo(db_session, world.firm_a).lines(world.project_a)

        assert line.task is None

    def test_a_line_left_pointing_at_a_removed_task_reads_as_unassigned(
        self, db_session, world, recipe_id, add_takeoff_line, add_task
    ):
        """The service clears the pointer when it removes a task. This is what a
        read says if one is ever left behind: the line is still listed, with no task."""
        task = add_task(world.project_a, world.firm_a, is_active=False)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", task=task)

        (line,) = repo(db_session, world.firm_a).lines(world.project_a)

        assert line.task is None


# What 1 m2 of the seeded wall costs: the six rows of
# test_the_wall_of_adr_003_computes_its_bricks_and_cement, 3,877,800.00 for 120 m2.
WALL_PER_M2 = Decimal("32315.00")


class TestCostByTask:
    """HU-13: a task costs what the take-off lines assigned to it cost."""

    def test_each_task_adds_up_its_own_lines_and_the_rest_is_unassigned(
        self, db_session, world, recipe_id, add_takeoff_line, add_task
    ):
        ground = add_task(world.project_a, world.firm_a, "Mampostería PB")
        upper = add_task(world.project_a, world.firm_a, "Mampostería PA")
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "70", task=ground)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "20", task=ground)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "50", task=upper)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "10")

        costs = repo(db_session, world.firm_a).cost_by_task(world.project_a)

        assert costs == {
            ground: 90 * WALL_PER_M2,
            upper: 50 * WALL_PER_M2,
            None: 10 * WALL_PER_M2,
        }

    def test_the_slices_add_up_to_the_whole_take_off(
        self, db_session, world, recipe_id, add_takeoff_line, add_task
    ):
        """Two ways of slicing the same lines: per task here, per resource in
        materials(). With amounts that do not need rounding they agree exactly."""
        task = add_task(world.project_a, world.firm_a)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "70", task=task)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[SUBFLOOR], "50")

        repository = repo(db_session, world.firm_a)
        by_task = repository.cost_by_task(world.project_a)
        by_resource = repository.materials(world.project_a)

        assert sum(by_task.values()) == sum(material.cost for material in by_resource)

    def test_a_cost_is_rounded_to_two_decimals(
        self, db_session, world, recipe_id, add_takeoff_line, add_task
    ):
        task = add_task(world.project_a, world.firm_a)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[SCREED], "33.333", task=task)

        cost = repo(db_session, world.firm_a).cost_by_task(world.project_a)[task]

        assert cost == cost.quantize(Decimal("0.01"))

    def test_a_task_with_no_lines_is_absent(self, db_session, world, add_task):
        """Not a zero: there is no row to group. The caller reads it with .get()."""
        add_task(world.project_a, world.firm_a)

        assert repo(db_session, world.firm_a).cost_by_task(world.project_a) == {}

    def test_a_removed_line_does_not_count(
        self, db_session, world, recipe_id, add_takeoff_line, add_task
    ):
        task = add_task(world.project_a, world.firm_a)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "10", task=task)
        add_takeoff_line(
            world.project_a, world.firm_a, recipe_id[WALL], "500", task=task, is_active=False
        )

        costs = repo(db_session, world.firm_a).cost_by_task(world.project_a)

        assert costs == {task: 10 * WALL_PER_M2}

    def test_a_line_left_pointing_at_a_removed_task_counts_as_unassigned(
        self, db_session, world, recipe_id, add_takeoff_line, add_task
    ):
        """Its money must not vanish from a planning that only lists live tasks."""
        removed = add_task(world.project_a, world.firm_a, is_active=False)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "10", task=removed)

        costs = repo(db_session, world.firm_a).cost_by_task(world.project_a)

        assert costs == {None: 10 * WALL_PER_M2}

    def test_another_firm_reads_no_costs(
        self, db_session, world, recipe_id, add_takeoff_line, add_task
    ):
        task = add_task(world.project_b, world.firm_b)
        add_takeoff_line(world.project_b, world.firm_b, recipe_id[WALL], "10", task=task)

        assert repo(db_session, world.firm_a).cost_by_task(world.project_b) == {}

    def test_another_work_of_the_same_firm_does_not_leak_in(
        self, db_session, world, recipe_id, add_takeoff_line, add_task, new_project
    ):
        other = new_project(world.firm_a, world.account_a, "Casa Otra")
        task = add_task(other, world.firm_a)
        add_takeoff_line(other, world.firm_a, recipe_id[WALL], "10", task=task)

        assert repo(db_session, world.firm_a).cost_by_task(world.project_a) == {}


class TestOneLine:
    def test_a_line_of_this_work_is_found(self, db_session, world, recipe_id, add_takeoff_line):
        line_id = add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")

        repository = repo(db_session, world.firm_a)

        assert repository.line(world.project_a, line_id).id == line_id
        assert repository.line_entry(world.project_a, line_id).recipe.name == WALL

    def test_a_removed_line_is_not_found(self, db_session, world, recipe_id, add_takeoff_line):
        line_id = add_takeoff_line(
            world.project_a, world.firm_a, recipe_id[WALL], "120", is_active=False
        )

        assert repo(db_session, world.firm_a).line(world.project_a, line_id) is None

    def test_a_line_of_another_work_of_the_same_firm_is_not_found(
        self, db_session, world, recipe_id, add_takeoff_line, new_project
    ):
        """The firm filter alone would let this through: the URL names work A,
        the line belongs to work B, and both are firm A's."""
        other = new_project(world.firm_a, world.account_a, "Casa Otra")
        line_id = add_takeoff_line(other, world.firm_a, recipe_id[WALL], "120")

        repository = repo(db_session, world.firm_a)

        assert repository.line(world.project_a, line_id) is None
        assert repository.line_entry(world.project_a, line_id) is None


class TestIsolation:
    @pytest.fixture
    def line_of_b(self, world, recipe_id, add_takeoff_line) -> int:
        return add_takeoff_line(world.project_b, world.firm_b, recipe_id[WALL], "120")

    def test_another_firm_reads_no_lines(self, db_session, world, line_of_b):
        """Even naming firm B's project and line outright, firm A's repository
        finds nothing: the tenant filter is on every read, not on the URL."""
        repository = repo(db_session, world.firm_a)

        assert repository.lines(world.project_b) == []
        assert repository.materials(world.project_b) == []
        assert repository.line(world.project_b, line_of_b) is None

    def test_another_work_of_the_same_firm_does_not_leak_in(
        self, db_session, world, recipe_id, add_takeoff_line, new_project
    ):
        other = new_project(world.firm_a, world.account_a, "Casa Otra")
        add_takeoff_line(other, world.firm_a, recipe_id[WALL], "120")

        repository = repo(db_session, world.firm_a)

        assert repository.lines(world.project_a) == []
        assert repository.materials(world.project_a) == []
