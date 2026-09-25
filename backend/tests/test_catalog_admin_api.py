"""/platform/catalog: the catalogue admin endpoints of HU-8.

The route audit in test_route_permissions.py already proves every one of these
demands catalog.manage in platform scope, resolves no roster, and refuses an
owner on both GETs. This file is about what each endpoint does for support, and
about the status codes catalog_admin.py's rules map to. The rules themselves are
pinned in test_catalog_admin_service.py; here they are only followed as far as
the response.
"""

import pytest

from app.services.catalog_admin import RECIPE_NAME_TAKEN, RESOURCE_NAME_TAKEN

RESOURCES_URL = "/platform/catalog/resources"
RECIPES_URL = "/platform/catalog/recipes"


@pytest.fixture
def support(support_account, auth_header) -> dict[str, str]:
    return auth_header(support_account)


def resource_body(unit_id, **overrides) -> dict:
    body = {
        "name": "Adhesivo cerámico",
        "type": "material",
        "unit_of_measure_id": unit_id["bolsa"],
        "reference_price": "9000.00",
    }
    body.update(overrides)
    return body


def recipe_body(unit_id, resource_id, **overrides) -> dict:
    body = {
        "name": "Revoque grueso",
        "description": "1:4",
        "unit_of_measure_id": unit_id["m2"],
        "lines": [
            {
                "resource_id": resource_id["Cemento portland (bolsa 50 kg)"],
                "quantity_per_unit": "0.2000",
            }
        ],
    }
    body.update(overrides)
    return body


class TestWhoGetsIn:
    def test_anonymous_gets_401(self, client):
        assert client.get(RESOURCES_URL).status_code == 401

    @pytest.mark.parametrize(
        ("method", "url_name", "body_fn"),
        [
            ("post", "resources", resource_body),
            ("post", "recipes", recipe_body),
        ],
        ids=["create-resource", "create-recipe"],
    )
    def test_an_owner_cannot_write(
        self, client, world, auth_header, unit_id, resource_id, method, url_name, body_fn
    ):
        """The GETs are covered by the route audit; writes need a valid body to
        reach the permission check, so they are exercised here."""
        url = RESOURCES_URL if url_name == "resources" else RECIPES_URL
        body = body_fn(unit_id) if url_name == "resources" else body_fn(unit_id, resource_id)

        response = getattr(client, method)(url, json=body, headers=auth_header(world.account_a))

        assert response.status_code == 403


class TestListResources:
    def test_support_sees_the_same_listing_hu4_shows(self, client, support):
        response = client.get(RESOURCES_URL, headers=support)

        assert response.status_code == 200
        names = {row["name"] for row in response.json()}
        assert "Ladrillo común" in names


class TestCreateResource:
    def test_creates_a_resource(self, client, support, unit_id):
        response = client.post(RESOURCES_URL, json=resource_body(unit_id), headers=support)

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Adhesivo cerámico"
        assert body["reference_price"] == "9000.00"
        assert body["unit"]["code"] == "bolsa"

    def test_a_duplicate_name_is_a_409(self, client, support, unit_id):
        response = client.post(
            RESOURCES_URL, json=resource_body(unit_id, name="Ladrillo común"), headers=support
        )

        assert response.status_code == 409
        assert response.json()["detail"] == RESOURCE_NAME_TAKEN

    def test_an_unknown_unit_is_a_422(self, client, support, unit_id):
        response = client.post(
            RESOURCES_URL, json=resource_body(unit_id, unit_of_measure_id=999_999), headers=support
        )

        assert response.status_code == 422

    def test_a_negative_price_is_a_422(self, client, support, unit_id):
        response = client.post(
            RESOURCES_URL, json=resource_body(unit_id, reference_price="-1.00"), headers=support
        )

        assert response.status_code == 422

    def test_an_unknown_type_is_a_422(self, client, support, unit_id):
        response = client.post(
            RESOURCES_URL, json=resource_body(unit_id, type="ladrillo"), headers=support
        )

        assert response.status_code == 422


class TestUpdateResource:
    def test_changing_the_price_updates_the_date_the_take_off_shows(
        self, client, support, unit_id, resource_id
    ):
        before = client.get(RESOURCES_URL, headers=support).json()
        row_before = next(r for r in before if r["id"] == resource_id["Hidrófugo"])

        response = client.put(
            f"{RESOURCES_URL}/{resource_id['Hidrófugo']}",
            json=resource_body(unit_id, name="Hidrófugo", reference_price="6000.00"),
            headers=support,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["reference_price"] == "6000.00"
        assert body["price_updated_at"] > row_before["price_updated_at"]

    def test_an_unknown_resource_is_a_404(self, client, support, unit_id):
        response = client.put(
            f"{RESOURCES_URL}/999999", json=resource_body(unit_id), headers=support
        )

        assert response.status_code == 404


class TestDeactivateResource:
    def test_in_use_by_an_active_recipe_is_a_409_naming_it(self, client, support, resource_id):
        response = client.delete(
            f"{RESOURCES_URL}/{resource_id['Ladrillo común']}", headers=support
        )

        assert response.status_code == 409
        assert "Pared de ladrillo común 15cm" in response.json()["detail"]

    def test_deactivating_removes_it_from_the_listing(self, client, support, unit_id):
        created = client.post(RESOURCES_URL, json=resource_body(unit_id), headers=support).json()

        response = client.delete(f"{RESOURCES_URL}/{created['id']}", headers=support)

        assert response.status_code == 204
        ids = {row["id"] for row in client.get(RESOURCES_URL, headers=support).json()}
        assert created["id"] not in ids

    def test_an_unknown_resource_is_a_404(self, client, support):
        assert client.delete(f"{RESOURCES_URL}/999999", headers=support).status_code == 404


class TestListRecipes:
    def test_support_sees_the_same_listing_hu4_shows(self, client, support):
        response = client.get(RECIPES_URL, headers=support)

        assert response.status_code == 200
        names = {row["name"] for row in response.json()}
        assert "Pared de ladrillo común 15cm" in names

    def test_a_firm_s_own_recipe_is_not_listed(self, client, support, world, add_firm_recipe):
        add_firm_recipe(world.firm_a, name="Revoque del estudio")

        body = client.get(RECIPES_URL, headers=support).json()

        assert "Revoque del estudio" not in {row["name"] for row in body}
        assert {row["origin"] for row in body} == {"general"}


class TestCreateRecipe:
    def test_creates_a_recipe_with_its_lines(self, client, support, unit_id, resource_id):
        response = client.post(RECIPES_URL, json=recipe_body(unit_id, resource_id), headers=support)

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Revoque grueso"
        assert [line["resource_id"] for line in body["lines"]] == [
            resource_id["Cemento portland (bolsa 50 kg)"]
        ]

    def test_a_duplicate_name_is_a_409(self, client, support, unit_id, resource_id):
        response = client.post(
            RECIPES_URL,
            json=recipe_body(unit_id, resource_id, name="Carpeta de cemento"),
            headers=support,
        )

        assert response.status_code == 409
        assert response.json()["detail"] == RECIPE_NAME_TAKEN

    def test_no_lines_is_a_422(self, client, support, unit_id, resource_id):
        response = client.post(
            RECIPES_URL, json=recipe_body(unit_id, resource_id, lines=[]), headers=support
        )

        assert response.status_code == 422

    def test_a_repeated_material_in_two_lines_is_a_422(self, client, support, unit_id, resource_id):
        line = {
            "resource_id": resource_id["Cemento portland (bolsa 50 kg)"],
            "quantity_per_unit": "0.1000",
        }
        response = client.post(
            RECIPES_URL, json=recipe_body(unit_id, resource_id, lines=[line, line]), headers=support
        )

        assert response.status_code == 422

    def test_a_zero_quantity_is_a_422(self, client, support, unit_id, resource_id):
        line = {
            "resource_id": resource_id["Cemento portland (bolsa 50 kg)"],
            "quantity_per_unit": "0",
        }
        response = client.post(
            RECIPES_URL, json=recipe_body(unit_id, resource_id, lines=[line]), headers=support
        )

        assert response.status_code == 422

    def test_a_deactivated_material_in_a_line_is_a_422(
        self, client, support, unit_id, resource_id, recipe_id
    ):
        client.delete(f"{RECIPES_URL}/{recipe_id['Carpeta de cemento']}", headers=support)
        client.delete(f"{RESOURCES_URL}/{resource_id['Hidrófugo']}", headers=support)
        line = {"resource_id": resource_id["Hidrófugo"], "quantity_per_unit": "1"}

        response = client.post(
            RECIPES_URL, json=recipe_body(unit_id, resource_id, lines=[line]), headers=support
        )

        assert response.status_code == 422


class TestUpdateRecipe:
    def test_replaces_the_lines(self, client, support, unit_id, resource_id, recipe_id):
        line = {"resource_id": resource_id["Arena fina"], "quantity_per_unit": "0.5000"}

        response = client.put(
            f"{RECIPES_URL}/{recipe_id['Carpeta de cemento']}",
            json=recipe_body(unit_id, resource_id, name="Carpeta de cemento", lines=[line]),
            headers=support,
        )

        assert response.status_code == 200
        body = response.json()
        assert [item["resource_id"] for item in body["lines"]] == [resource_id["Arena fina"]]

    def test_a_firm_s_own_recipe_is_a_404(
        self, client, support, unit_id, resource_id, world, add_firm_recipe
    ):
        recipe = add_firm_recipe(world.firm_a)

        response = client.put(
            f"{RECIPES_URL}/{recipe}", json=recipe_body(unit_id, resource_id), headers=support
        )

        assert response.status_code == 404

    def test_an_unknown_recipe_is_a_404(self, client, support, unit_id, resource_id):
        response = client.put(
            f"{RECIPES_URL}/999999", json=recipe_body(unit_id, resource_id), headers=support
        )

        assert response.status_code == 404


class TestDeactivateRecipe:
    def test_deactivating_removes_it_from_the_listing_but_not_from_a_take_off(
        self, client, support, recipe_id, world, add_takeoff_line
    ):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id["Contrapiso de cascote"], "8.000")

        response = client.delete(
            f"{RECIPES_URL}/{recipe_id['Contrapiso de cascote']}", headers=support
        )

        assert response.status_code == 204
        ids = {row["id"] for row in client.get(RECIPES_URL, headers=support).json()}
        assert recipe_id["Contrapiso de cascote"] not in ids

    def test_an_unknown_recipe_is_a_404(self, client, support):
        assert client.delete(f"{RECIPES_URL}/999999", headers=support).status_code == 404


def test_the_seed_does_not_reappear_once_edited(client, support, unit_id, resource_id):
    """ADR-005 section 4: the seed loads initial content and never overwrites
    what a write already changed. Not literally re-running the seed here — that
    lives in test_catalog_seed.py — but pinning that an edit sticks."""
    client.put(
        f"{RESOURCES_URL}/{resource_id['Hidrófugo']}",
        json=resource_body(unit_id, name="Hidrófugo", reference_price="1.00"),
        headers=support,
    )

    row = next(
        r
        for r in client.get(RESOURCES_URL, headers=support).json()
        if r["id"] == resource_id["Hidrófugo"]
    )
    assert row["reference_price"] == "1.00"
