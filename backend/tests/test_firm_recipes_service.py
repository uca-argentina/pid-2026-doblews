"""The rules for a firm writing its own recipes (HU-9, ADR-006), on the service.

The status codes are test_catalog_api.py's business; here it is what gets
written, and what a firm can and cannot reach. Firm A is the one writing;
firm B is the one it must never touch.
"""

from decimal import Decimal

import pytest

from app.models import Recipe, RecipeResource
from app.repositories.project_recipe import ProjectRecipeRepository
from app.services.catalog_admin import (
    RECIPE_NEEDS_A_LINE,
    CatalogError,
    InvalidReferenceError,
    RecipeLineInput,
    RecipeNotFoundError,
)
from app.services.firm_recipes import (
    FIRM_RECIPE_NAME_TAKEN,
    create_firm_recipe,
    deactivate_firm_recipe,
    update_firm_recipe,
)

WALL = "Pared de ladrillo común 15cm"
BRICK = "Ladrillo común"
CEMENT = "Cemento portland (bolsa 50 kg)"


def write(db_session, firm_id, unit_id, resource_id, *, name="Revoque del estudio", **overrides):
    """Create a recipe for this firm with one line of cement, unless told otherwise."""
    fields = {
        "name": name,
        "description": "1:4",
        "unit_of_measure_id": unit_id["m2"],
        "lines": [RecipeLineInput(resource_id[CEMENT], Decimal("0.2000"))],
    } | overrides
    return create_firm_recipe(db_session, firm_id, **fields)


def lines_of(db_session, recipe_id: int) -> dict[int, Decimal]:
    rows = db_session.query(RecipeResource).filter_by(recipe_id=recipe_id).all()
    return {row.resource_id: row.quantity_per_unit for row in rows}


class TestCreate:
    def test_the_recipe_belongs_to_the_firm_it_was_written_for(
        self, db_session, world, unit_id, resource_id
    ):
        recipe = write(db_session, world.firm_a, unit_id, resource_id)

        assert (recipe.firm_id, recipe.is_active) == (world.firm_a, True)
        assert lines_of(db_session, recipe.id) == {resource_id[CEMENT]: Decimal("0.2000")}

    def test_refuses_a_name_the_firm_already_uses(self, db_session, world, unit_id, resource_id):
        write(db_session, world.firm_a, unit_id, resource_id)

        with pytest.raises(CatalogError) as refused:
            write(db_session, world.firm_a, unit_id, resource_id, name="REVOQUE DEL ESTUDIO")

        assert refused.value.detail == FIRM_RECIPE_NAME_TAKEN

    def test_may_share_a_general_recipe_s_name(self, db_session, world, unit_id, resource_id):
        """HU-9: the origin tells them apart."""
        recipe = write(db_session, world.firm_a, unit_id, resource_id, name=WALL)

        assert recipe.firm_id == world.firm_a

    def test_may_share_another_firm_s_recipe_name(self, db_session, world, unit_id, resource_id):
        write(db_session, world.firm_b, unit_id, resource_id)

        recipe = write(db_session, world.firm_a, unit_id, resource_id)

        assert recipe.firm_id == world.firm_a

    def test_refuses_an_empty_set_of_lines(self, db_session, world, unit_id, resource_id):
        with pytest.raises(CatalogError) as refused:
            write(db_session, world.firm_a, unit_id, resource_id, lines=[])

        assert refused.value.detail == RECIPE_NEEDS_A_LINE

    def test_refuses_a_deactivated_system_resource(
        self, db, db_session, world, unit_id, resource_id
    ):
        """ADR-006 rule 3: only active resources of the system catalogue."""
        db.exec_driver_sql(
            "UPDATE resource SET is_active = false WHERE id = %s", (resource_id[CEMENT],)
        )

        with pytest.raises(InvalidReferenceError):
            write(db_session, world.firm_a, unit_id, resource_id)

        assert db_session.query(Recipe).filter_by(firm_id=world.firm_a).count() == 0


class TestUpdate:
    def test_replaces_the_header_and_every_line(self, db_session, world, unit_id, resource_id):
        recipe = write(db_session, world.firm_a, unit_id, resource_id)

        update_firm_recipe(
            db_session,
            world.firm_a,
            recipe.id,
            name="Revoque fino",
            description=None,
            unit_of_measure_id=unit_id["m2"],
            lines=[RecipeLineInput(resource_id[BRICK], Decimal("10"))],
        )

        assert (recipe.name, recipe.description) == ("Revoque fino", None)
        assert lines_of(db_session, recipe.id) == {resource_id[BRICK]: Decimal("10.0000")}

    def test_keeping_its_own_name_is_not_a_collision(self, db_session, world, unit_id, resource_id):
        recipe = write(db_session, world.firm_a, unit_id, resource_id)

        update_firm_recipe(
            db_session,
            world.firm_a,
            recipe.id,
            name=recipe.name,
            description="otra nota",
            unit_of_measure_id=unit_id["m2"],
            lines=[RecipeLineInput(resource_id[CEMENT], Decimal("0.3"))],
        )

        assert recipe.description == "otra nota"

    def test_a_general_recipe_is_not_found(
        self, db_session, world, unit_id, resource_id, recipe_id
    ):
        """ADR-006 rule 2: a firm's routes never write the system catalogue."""
        with pytest.raises(RecipeNotFoundError):
            update_firm_recipe(
                db_session,
                world.firm_a,
                recipe_id[WALL],
                name="Pared mía",
                description=None,
                unit_of_measure_id=unit_id["m2"],
                lines=[RecipeLineInput(resource_id[BRICK], Decimal("1"))],
            )

        assert db_session.get(Recipe, recipe_id[WALL]).name == WALL

    def test_another_firm_s_recipe_is_not_found(self, db_session, world, unit_id, resource_id):
        theirs = write(db_session, world.firm_b, unit_id, resource_id)

        with pytest.raises(RecipeNotFoundError):
            update_firm_recipe(
                db_session,
                world.firm_a,
                theirs.id,
                name="Ahora es mía",
                description=None,
                unit_of_measure_id=unit_id["m2"],
                lines=[RecipeLineInput(resource_id[BRICK], Decimal("1"))],
            )


class TestDeactivate:
    def test_deactivates_it(self, db_session, world, unit_id, resource_id):
        recipe = write(db_session, world.firm_a, unit_id, resource_id)

        deactivate_firm_recipe(db_session, world.firm_a, recipe.id)

        assert recipe.is_active is False

    def test_a_take_off_already_using_it_keeps_its_line(
        self, db_session, world, unit_id, resource_id, add_takeoff_line
    ):
        """Same as a general recipe (ADR-005 section 6): no usage guard, and the
        line keeps computing because it points at the recipe, not at the listing."""
        recipe = write(db_session, world.firm_a, unit_id, resource_id)
        add_takeoff_line(world.project_a, world.firm_a, recipe.id, "10")

        deactivate_firm_recipe(db_session, world.firm_a, recipe.id)

        materials = ProjectRecipeRepository(db_session, firm_id=world.firm_a).materials(
            world.project_a
        )
        # 10 m2 x 0.2 bags per m2.
        assert {m.name: m.quantity for m in materials} == {CEMENT: Decimal("2")}

    def test_frees_its_name_for_a_new_one(self, db_session, world, unit_id, resource_id):
        recipe = write(db_session, world.firm_a, unit_id, resource_id)
        deactivate_firm_recipe(db_session, world.firm_a, recipe.id)

        again = write(db_session, world.firm_a, unit_id, resource_id)

        assert again.id != recipe.id

    def test_a_general_recipe_is_not_found(self, db_session, world, recipe_id):
        with pytest.raises(RecipeNotFoundError):
            deactivate_firm_recipe(db_session, world.firm_a, recipe_id[WALL])

        assert db_session.get(Recipe, recipe_id[WALL]).is_active is True

    def test_another_firm_s_recipe_is_not_found(self, db_session, world, unit_id, resource_id):
        theirs = write(db_session, world.firm_b, unit_id, resource_id)

        with pytest.raises(RecipeNotFoundError):
            deactivate_firm_recipe(db_session, world.firm_a, theirs.id)

        assert theirs.is_active is True
