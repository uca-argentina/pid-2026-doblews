"""The catalogue admin rules of HU-8, tested on the service without HTTP in the way.

resource_id and recipe_id map the seed's names to ids (T-04: seven materials,
three recipes — see ce50de774991_seed_system_catalog.py). unit_id maps a unit's
code to its id.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select, text

from app.models import Recipe, Resource
from app.services.catalog_admin import (
    RECIPE_NAME_TAKEN,
    RECIPE_NEEDS_A_LINE,
    RESOURCE_NAME_TAKEN,
    CatalogError,
    InvalidReferenceError,
    RecipeLineInput,
    RecipeNotFoundError,
    ResourceNotFoundError,
    create_recipe,
    create_resource,
    deactivate_recipe,
    deactivate_resource,
    get_recipe,
    get_resource,
    update_recipe,
    update_resource,
)


def make_resource(db_session, unit_id, *, name="Adhesivo cerámico", price="9000.00"):
    return create_resource(
        db_session,
        name=name,
        type="material",
        unit_of_measure_id=unit_id["bolsa"],
        reference_price=Decimal(price),
    )


class TestGetResource:
    def test_an_unknown_resource_is_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundError):
            get_resource(db_session, 999_999)


class TestGetRecipe:
    def test_an_unknown_recipe_is_not_found(self, db_session):
        with pytest.raises(RecipeNotFoundError):
            get_recipe(db_session, 999_999)


class TestCreateResource:
    def test_creates_an_active_resource(self, db_session, unit_id):
        resource = make_resource(db_session, unit_id)

        assert (resource.name, resource.type, resource.is_active) == (
            "Adhesivo cerámico",
            "material",
            True,
        )
        assert resource.currency == "ARS"

    def test_refuses_a_name_already_active_case_insensitively(self, db_session, unit_id):
        with pytest.raises(CatalogError) as error:
            create_resource(
                db_session,
                name="ladrillo común",
                type="material",
                unit_of_measure_id=unit_id["u"],
                reference_price=Decimal("1"),
            )

        assert error.value.detail == RESOURCE_NAME_TAKEN

    def test_a_deactivated_name_is_free_to_reuse(self, db_session, unit_id, resource_id, recipe_id):
        # Hidrófugo is a line of "Carpeta de cemento" in the seed, so that
        # recipe has to go first (ADR-005 section 6).
        deactivate_recipe(db_session, recipe_id["Carpeta de cemento"])
        deactivate_resource(db_session, resource_id["Hidrófugo"])

        resource = create_resource(
            db_session,
            name="Hidrófugo",
            type="material",
            unit_of_measure_id=unit_id["kg"],
            reference_price=Decimal("5000.00"),
        )

        assert resource.name == "Hidrófugo"

    def test_refuses_an_unknown_unit(self, db_session, unit_id):
        with pytest.raises(InvalidReferenceError):
            create_resource(
                db_session,
                name="Nuevo material",
                type="material",
                unit_of_measure_id=999_999,
                reference_price=Decimal("1"),
            )

    def test_writes_nothing_when_the_unit_is_invalid(self, db_session, unit_id):
        before = db_session.scalar(select(Resource.id).order_by(Resource.id.desc()))

        with pytest.raises(InvalidReferenceError):
            create_resource(
                db_session,
                name="Nuevo material",
                type="material",
                unit_of_measure_id=999_999,
                reference_price=Decimal("1"),
            )

        assert db_session.scalar(select(Resource.id).order_by(Resource.id.desc())) == before


class TestUpdateResource:
    def test_renaming_does_not_move_the_price_date(self, db_session, resource_id, unit_id):
        resource = get_resource(db_session, resource_id["Hidrófugo"])
        price_before = resource.price_updated_at

        updated = update_resource(
            db_session,
            resource.id,
            name="Hidrófugo líquido",
            type="material",
            unit_of_measure_id=unit_id["kg"],
            reference_price=resource.reference_price,
        )

        assert updated.name == "Hidrófugo líquido"
        assert updated.price_updated_at == price_before

    def test_changing_the_price_moves_the_price_date(self, db_session, resource_id):
        resource = get_resource(db_session, resource_id["Hidrófugo"])
        price_before = resource.price_updated_at

        updated = update_resource(
            db_session,
            resource.id,
            name=resource.name,
            type=resource.type,
            unit_of_measure_id=resource.unit_of_measure_id,
            reference_price=Decimal("5555.55"),
        )

        assert updated.reference_price == Decimal("5555.55")
        assert updated.price_updated_at > price_before

    def test_keeping_its_own_name_is_not_a_collision(self, db_session, resource_id):
        resource = get_resource(db_session, resource_id["Hidrófugo"])

        updated = update_resource(
            db_session,
            resource.id,
            name="Hidrófugo",
            type=resource.type,
            unit_of_measure_id=resource.unit_of_measure_id,
            reference_price=resource.reference_price,
        )

        assert updated.name == "Hidrófugo"

    def test_refuses_another_active_resource_s_name(self, db_session, resource_id, unit_id):
        with pytest.raises(CatalogError) as error:
            update_resource(
                db_session,
                resource_id["Hidrófugo"],
                name="Cascote",
                type="material",
                unit_of_measure_id=unit_id["kg"],
                reference_price=Decimal("1"),
            )

        assert error.value.detail == RESOURCE_NAME_TAKEN

    def test_an_unknown_resource_is_not_found(self, db_session, unit_id):
        with pytest.raises(ResourceNotFoundError):
            update_resource(
                db_session,
                999_999,
                name="X",
                type="material",
                unit_of_measure_id=unit_id["kg"],
                reference_price=Decimal("1"),
            )


class TestDeactivateResource:
    def test_deactivates_a_resource_nothing_uses(self, db_session, unit_id):
        resource = make_resource(db_session, unit_id)

        deactivate_resource(db_session, resource.id)

        assert db_session.get(Resource, resource.id).is_active is False

    def test_refuses_a_resource_an_active_recipe_uses_and_names_it(
        self, db_session, resource_id, recipe_id
    ):
        with pytest.raises(CatalogError) as error:
            deactivate_resource(db_session, resource_id["Ladrillo común"])

        assert "Pared de ladrillo común 15cm" in error.value.detail

    def test_freed_once_the_recipe_is_deactivated(self, db_session, resource_id, recipe_id):
        deactivate_recipe(db_session, recipe_id["Pared de ladrillo común 15cm"])

        deactivate_resource(db_session, resource_id["Ladrillo común"])

        assert db_session.get(Resource, resource_id["Ladrillo común"]).is_active is False

    def test_an_unknown_resource_is_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundError):
            deactivate_resource(db_session, 999_999)

    def test_a_deactivated_resource_is_not_found_again(self, db_session, unit_id):
        resource = make_resource(db_session, unit_id)
        deactivate_resource(db_session, resource.id)

        with pytest.raises(ResourceNotFoundError):
            deactivate_resource(db_session, resource.id)


class TestCreateRecipe:
    def test_creates_a_recipe_with_its_lines(self, db_session, unit_id, resource_id):
        recipe = create_recipe(
            db_session,
            name="Revoque grueso",
            description="1:4",
            unit_of_measure_id=unit_id["m2"],
            lines=[
                RecipeLineInput(
                    resource_id=resource_id["Cemento portland (bolsa 50 kg)"],
                    quantity_per_unit=Decimal("0.2000"),
                ),
                RecipeLineInput(
                    resource_id=resource_id["Arena gruesa"], quantity_per_unit=Decimal("0.0400")
                ),
            ],
        )

        rows = db_session.execute(
            text("SELECT resource_id FROM recipe_resource WHERE recipe_id = :r"),
            {"r": recipe.id},
        ).all()
        assert len(rows) == 2

    def test_refuses_an_empty_set_of_lines(self, db_session, unit_id):
        with pytest.raises(CatalogError) as error:
            create_recipe(
                db_session,
                name="Vacía",
                description=None,
                unit_of_measure_id=unit_id["m2"],
                lines=[],
            )

        assert error.value.detail == RECIPE_NEEDS_A_LINE

    def test_refuses_a_name_already_active(self, db_session, unit_id, resource_id):
        with pytest.raises(CatalogError) as error:
            create_recipe(
                db_session,
                name="Contrapiso de cascote",
                description=None,
                unit_of_measure_id=unit_id["m2"],
                lines=[
                    RecipeLineInput(
                        resource_id=resource_id["Cascote"], quantity_per_unit=Decimal("1")
                    )
                ],
            )

        assert error.value.detail == RECIPE_NAME_TAKEN

    def test_refuses_a_line_pointing_at_a_deactivated_resource(
        self, db_session, unit_id, resource_id, recipe_id
    ):
        deactivate_recipe(db_session, recipe_id["Carpeta de cemento"])
        deactivate_resource(db_session, resource_id["Hidrófugo"])

        with pytest.raises(InvalidReferenceError):
            create_recipe(
                db_session,
                name="Receta nueva",
                description=None,
                unit_of_measure_id=unit_id["m2"],
                lines=[
                    RecipeLineInput(
                        resource_id=resource_id["Hidrófugo"], quantity_per_unit=Decimal("1")
                    )
                ],
            )

    def test_refuses_a_line_pointing_at_an_unknown_resource(self, db_session, unit_id):
        with pytest.raises(InvalidReferenceError):
            create_recipe(
                db_session,
                name="Receta nueva",
                description=None,
                unit_of_measure_id=unit_id["m2"],
                lines=[RecipeLineInput(resource_id=999_999, quantity_per_unit=Decimal("1"))],
            )


class TestUpdateRecipe:
    def test_replaces_the_lines_entirely(self, db_session, unit_id, resource_id, recipe_id):
        recipe = update_recipe(
            db_session,
            recipe_id["Carpeta de cemento"],
            name="Carpeta de cemento",
            description="editada",
            unit_of_measure_id=unit_id["m2"],
            lines=[
                RecipeLineInput(
                    resource_id=resource_id["Arena fina"], quantity_per_unit=Decimal("0.5000")
                )
            ],
        )

        rows = db_session.execute(
            text("SELECT resource_id, quantity_per_unit FROM recipe_resource WHERE recipe_id = :r"),
            {"r": recipe.id},
        ).all()
        assert [(row.resource_id, row.quantity_per_unit) for row in rows] == [
            (resource_id["Arena fina"], Decimal("0.5000"))
        ]

    def test_refuses_replacing_with_an_empty_set_of_lines(self, db_session, unit_id, recipe_id):
        with pytest.raises(CatalogError) as error:
            update_recipe(
                db_session,
                recipe_id["Carpeta de cemento"],
                name="Carpeta de cemento",
                description=None,
                unit_of_measure_id=unit_id["m2"],
                lines=[],
            )

        assert error.value.detail == RECIPE_NEEDS_A_LINE

    def test_a_take_off_already_using_it_is_unaffected(
        self, db_session, unit_id, resource_id, recipe_id, add_takeoff_line, world
    ):
        add_takeoff_line(
            world.project_a, world.firm_a, recipe_id["Contrapiso de cascote"], "10.000"
        )

        update_recipe(
            db_session,
            recipe_id["Contrapiso de cascote"],
            name="Contrapiso de cascote",
            description="reformada",
            unit_of_measure_id=unit_id["m2"],
            lines=[
                RecipeLineInput(
                    resource_id=resource_id["Cascote"], quantity_per_unit=Decimal("0.2000")
                )
            ],
        )

        line_count = db_session.execute(
            text("SELECT count(*) FROM project_recipe WHERE recipe_id = :r AND is_active"),
            {"r": recipe_id["Contrapiso de cascote"]},
        ).scalar_one()
        assert line_count == 1

    def test_an_unknown_recipe_is_not_found(self, db_session, unit_id, resource_id):
        with pytest.raises(RecipeNotFoundError):
            update_recipe(
                db_session,
                999_999,
                name="X",
                description=None,
                unit_of_measure_id=unit_id["m2"],
                lines=[
                    RecipeLineInput(
                        resource_id=resource_id["Cascote"], quantity_per_unit=Decimal("1")
                    )
                ],
            )


class TestDeactivateRecipe:
    def test_deactivates_it(self, db_session, recipe_id):
        deactivate_recipe(db_session, recipe_id["Carpeta de cemento"])

        assert db_session.get(Recipe, recipe_id["Carpeta de cemento"]).is_active is False

    def test_carries_no_usage_guard(self, db_session, recipe_id, add_takeoff_line, world):
        """ADR-005 section 6: a take-off that already uses it keeps computing."""
        add_takeoff_line(world.project_a, world.firm_a, recipe_id["Carpeta de cemento"], "5.000")

        deactivate_recipe(db_session, recipe_id["Carpeta de cemento"])

        assert db_session.get(Recipe, recipe_id["Carpeta de cemento"]).is_active is False

    def test_an_unknown_recipe_is_not_found(self, db_session):
        with pytest.raises(RecipeNotFoundError):
            deactivate_recipe(db_session, 999_999)
