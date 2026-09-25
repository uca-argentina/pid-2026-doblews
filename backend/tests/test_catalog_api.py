"""GET /firms/{firm_id}/catalog/...: the system catalogue as HU-4 shows it.

What the seed holds is pinned in test_catalog_seed.py; what is under test here
is what the endpoints make of it. That a recipe arrives with its lines and their
prices, that the numbers keep their decimals on the wire, that a deactivated row
drops out, and that every firm role holding catalog.view reads the same thing.

Someone outside the firm getting a 404 is not repeated here: the isolation suite
in test_route_permissions.py walks these routes like every other.

Ana owns firm A; Clara is a firm client of A.
"""

import pytest
from sqlalchemy import text

from app.services.firm_recipes import FIRM_RECIPE_NAME_TAKEN

WALL = "Pared de ladrillo común 15cm"
BRICK = "Ladrillo común"
CEMENT = "Cemento portland (bolsa 50 kg)"


def recipes(client, firm_id, headers):
    return client.get(f"/firms/{firm_id}/catalog/recipes", headers=headers)


def resources(client, firm_id, headers):
    return client.get(f"/firms/{firm_id}/catalog/resources", headers=headers)


@pytest.fixture
def clara(world, new_member):
    return new_member(world.firm_a, "clara@test.com", "client")


class TestRecipes:
    def test_lists_the_active_recipes_by_name(self, client, world, auth_header):
        response = recipes(client, world.firm_a, auth_header(world.account_a))

        assert response.status_code == 200
        names = [recipe["name"] for recipe in response.json()]
        assert names == [
            "Carpeta de cemento",
            "Contrapiso de cascote",
            WALL,
        ]

    def test_lists_this_firm_s_own_recipes_with_their_origin(
        self, client, world, auth_header, add_firm_recipe
    ):
        """HU-9: the general recipes and this firm's, each saying which it is."""
        add_firm_recipe(world.firm_a, name="Revoque del estudio")

        body = recipes(client, world.firm_a, auth_header(world.account_a)).json()

        origin = {recipe["name"]: recipe["origin"] for recipe in body}
        assert origin["Revoque del estudio"] == "firm"
        assert origin[WALL] == "general"

    def test_another_firm_s_recipe_never_appears(self, client, world, auth_header, add_firm_recipe):
        """ADR-006: a firm's recipe is its content, invisible to every other firm."""
        add_firm_recipe(world.firm_b, name="Revoque de Sur")

        body = recipes(client, world.firm_a, auth_header(world.account_a)).json()

        assert "Revoque de Sur" not in {recipe["name"] for recipe in body}

    def test_a_recipe_arrives_with_what_one_unit_of_it_takes(self, client, world, auth_header):
        """ADR-003's own example, typed out: 1 m2 of wall takes 60 bricks and a
        quarter of a bag of cement."""
        body = recipes(client, world.firm_a, auth_header(world.account_a)).json()
        wall = next(recipe for recipe in body if recipe["name"] == WALL)

        assert wall["unit"] == {"code": "m2", "abbreviation": "m2"}
        assert wall["description"]
        lines = {line["name"]: line for line in wall["lines"]}
        assert lines[BRICK]["quantity_per_unit"] == "60.0000"
        assert lines[BRICK]["unit"]["code"] == "u"
        assert lines[CEMENT]["quantity_per_unit"] == "0.2500"
        assert lines[CEMENT]["unit"]["code"] == "bolsa"

    def test_each_line_carries_its_material_price_as_a_decimal_string(
        self, client, world, auth_header
    ):
        body = recipes(client, world.firm_a, auth_header(world.account_a)).json()
        wall = next(recipe for recipe in body if recipe["name"] == WALL)
        brick = next(line for line in wall["lines"] if line["name"] == BRICK)

        assert brick["reference_price"] == "230.00"
        assert brick["currency"] == "ARS"

    def test_a_deactivated_recipe_is_not_offered(self, client, world, auth_header, db):
        db.execute(text("UPDATE recipe SET is_active = false WHERE name = :n"), {"n": WALL})

        body = recipes(client, world.firm_a, auth_header(world.account_a)).json()

        assert WALL not in {recipe["name"] for recipe in body}


class TestResources:
    def test_lists_the_active_resources_by_name_with_their_price(self, client, world, auth_header):
        response = resources(client, world.firm_a, auth_header(world.account_a))

        assert response.status_code == 200
        body = response.json()
        names = [resource["name"] for resource in body]
        assert names == sorted(names)
        assert len(body) == 10

        brick = next(resource for resource in body if resource["name"] == BRICK)
        assert brick["type"] == "material"
        assert brick["unit"] == {"code": "u", "abbreviation": "u"}
        assert brick["reference_price"] == "230.00"
        assert brick["currency"] == "ARS"
        assert brick["price_updated_at"]

    def test_a_deactivated_resource_is_not_listed(self, client, world, auth_header, db):
        db.execute(text("UPDATE resource SET is_active = false WHERE name = :n"), {"n": BRICK})

        body = resources(client, world.firm_a, auth_header(world.account_a)).json()

        assert BRICK not in {resource["name"] for resource in body}


class TestWhoReadsIt:
    def test_a_firm_client_reads_the_catalogue_prices_included(
        self, client, world, auth_header, clara
    ):
        """catalog.view is granted to client too (ADR-003 section 8). Reference
        prices are the platform's, not the firm's costs, so they are not hidden."""
        headers = auth_header(clara)

        assert recipes(client, world.firm_a, headers).status_code == 200
        body = resources(client, world.firm_a, headers).json()
        assert all(resource["reference_price"] for resource in body)

    def test_every_firm_reads_the_same_catalogue(self, client, world, auth_header):
        """Global to the platform: firm B's owner gets exactly what firm A's does."""
        from_a = recipes(client, world.firm_a, auth_header(world.account_a)).json()
        from_b = recipes(client, world.firm_b, auth_header(world.account_b)).json()

        assert from_a == from_b


def recipe_body(unit_id, resource_id, **overrides) -> dict:
    body = {
        "name": "Revoque del estudio",
        "description": "1:4",
        "unit_of_measure_id": unit_id["m2"],
        "lines": [{"resource_id": resource_id[CEMENT], "quantity_per_unit": "0.2000"}],
    }
    body.update(overrides)
    return body


class TestFirmRecipeWrites:
    """HU-9: owner and architect write their firm's recipes, and only those."""

    @pytest.mark.parametrize("who", ["owner", "architect"])
    def test_owner_and_architect_create_one(
        self, client, world, auth_header, unit_id, resource_id, who
    ):
        account = world.account_a if who == "owner" else world.account_a2

        response = client.post(
            f"/firms/{world.firm_a}/catalog/recipes",
            json=recipe_body(unit_id, resource_id),
            headers=auth_header(account),
        )

        assert response.status_code == 201
        body = response.json()
        assert (body["name"], body["origin"]) == ("Revoque del estudio", "firm")
        listed = recipes(client, world.firm_a, auth_header(account)).json()
        assert body["id"] in {recipe["id"] for recipe in listed}

    def test_the_client_reads_them_but_cannot_write(
        self, client, world, clara, auth_header, unit_id, resource_id, add_firm_recipe
    ):
        """catalog.view without recipe.manage (ADR-006 section 3)."""
        add_firm_recipe(world.firm_a, name="Revoque del estudio")

        listed = recipes(client, world.firm_a, auth_header(clara)).json()
        response = client.post(
            f"/firms/{world.firm_a}/catalog/recipes",
            json=recipe_body(unit_id, resource_id, name="Otra"),
            headers=auth_header(clara),
        )

        assert "Revoque del estudio" in {recipe["name"] for recipe in listed}
        assert response.status_code == 403

    def test_a_name_the_firm_already_uses_is_a_409(
        self, client, world, auth_header, unit_id, resource_id, add_firm_recipe
    ):
        add_firm_recipe(world.firm_a, name="Revoque del estudio")

        response = client.post(
            f"/firms/{world.firm_a}/catalog/recipes",
            json=recipe_body(unit_id, resource_id),
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == FIRM_RECIPE_NAME_TAKEN

    def test_a_general_recipe_s_name_is_allowed(
        self, client, world, auth_header, unit_id, resource_id
    ):
        response = client.post(
            f"/firms/{world.firm_a}/catalog/recipes",
            json=recipe_body(unit_id, resource_id, name=WALL),
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 201

    def test_editing_replaces_it(
        self, client, world, auth_header, unit_id, resource_id, add_firm_recipe
    ):
        recipe = add_firm_recipe(world.firm_a)

        response = client.put(
            f"/firms/{world.firm_a}/catalog/recipes/{recipe}",
            json=recipe_body(unit_id, resource_id, name="Revoque fino"),
            headers=auth_header(world.account_a2),
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Revoque fino"
        assert [line["resource_id"] for line in response.json()["lines"]] == [resource_id[CEMENT]]

    def test_deactivating_drops_it_from_the_listing(
        self, client, world, auth_header, add_firm_recipe
    ):
        recipe = add_firm_recipe(world.firm_a)

        response = client.delete(
            f"/firms/{world.firm_a}/catalog/recipes/{recipe}",
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 204
        listed = recipes(client, world.firm_a, auth_header(world.account_a)).json()
        assert recipe not in {row["id"] for row in listed}

    @pytest.mark.parametrize("method", ["put", "delete"])
    def test_a_general_recipe_is_a_404(
        self, client, world, auth_header, unit_id, resource_id, recipe_id, method
    ):
        """ADR-006 rule 2: no firm route writes the system catalogue, and it
        answers as if the recipe were not there."""
        response = client.request(
            method.upper(),
            f"/firms/{world.firm_a}/catalog/recipes/{recipe_id[WALL]}",
            json=recipe_body(unit_id, resource_id) if method == "put" else None,
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 404

    @pytest.mark.parametrize("method", ["put", "delete"])
    def test_another_firm_s_recipe_is_a_404(
        self, client, world, auth_header, unit_id, resource_id, add_firm_recipe, method
    ):
        theirs = add_firm_recipe(world.firm_b)

        response = client.request(
            method.upper(),
            f"/firms/{world.firm_a}/catalog/recipes/{theirs}",
            json=recipe_body(unit_id, resource_id) if method == "put" else None,
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 404
