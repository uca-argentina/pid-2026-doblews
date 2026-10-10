"""Pins the budget-version endpoints at the border: who gets which status code.
The rules and the numbers are pinned in the service tests; here it is the two
permissions of ADR-007 section 4, the 404s that keep other works invisible, and
the shape of the answers the screen reads.
"""

import pytest
from sqlalchemy import text

from app.services.budget_versions import EMPTY_TAKEOFF

WALL = "Pared de ladrillo común 15cm"
SUBFLOOR = "Contrapiso de cascote"


def versions_url(world, project_id: int | None = None, version_id: int | None = None) -> str:
    base = f"/firms/{world.firm_a}/projects/{project_id or world.project_a}/budget/versions"
    return base if version_id is None else f"{base}/{version_id}"


def archive(db, project_id: int) -> None:
    """Archive a work behind the API's back, as HU-3's DELETE does."""
    db.execute(text("UPDATE project SET is_active = false WHERE id = :p"), {"p": project_id})


def group(body, type_: str) -> dict:
    return next(found for found in body["groups"] if found["type"] == type_)


@pytest.fixture
def team(world, new_member, add_project_member):
    """The same cast as HU-5's and HU-11's tests, so the three are compared on
    the same people: what changes between them is the guard, not the roster."""
    collaborator = new_member(world.firm_a, "carlos@test.com", "architect")
    client = new_member(world.firm_a, "clara@test.com", "client")
    bystander = new_member(world.firm_a, "otto@test.com", "architect")

    add_project_member(world.project_a, world.account_a2, world.firm_a, "lead")
    add_project_member(world.project_a, collaborator, world.firm_a, "collaborator")
    add_project_member(world.project_a, client, world.firm_a, "client")

    return {
        "lead": world.account_a2,
        "collaborator": collaborator,
        "client": client,
        "owner": world.account_a,
        "bystander": bystander,
        "stranger": world.account_b,
    }


@pytest.fixture
def wall(world, recipe_id, add_takeoff_line) -> int:
    return add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", note="PB")


@pytest.fixture
def version(client, world, team, wall, auth_header) -> dict:
    """One saved version of work A, created through the API it is testing.

    Through the API and not through SQL, unlike the take-off fixtures: here the
    thing under test is the whole round trip, and a version inserted by hand
    would not prove that what is saved is what is read back.
    """
    return client.post(
        versions_url(world),
        json={"note": "Presentado al cliente"},
        headers=auth_header(team["lead"]),
    ).json()


class TestSave:
    @pytest.mark.parametrize("role", ["lead", "collaborator"])
    def test_these_roles_save_a_version(self, client, world, team, wall, auth_header, role):
        response = client.post(
            versions_url(world), json={"note": None}, headers=auth_header(team[role])
        )

        assert response.status_code == 201
        assert response.json()["version_number"] == 1

    @pytest.mark.parametrize("role", ["client", "owner"])
    def test_these_roles_cannot_save(self, client, world, team, wall, auth_header, role):
        """The owner is the interesting one: project.view_all opens the reading
        and never the writing — auditing a work is not deciding what gets
        presented to its client."""
        response = client.post(
            versions_url(world), json={"note": None}, headers=auth_header(team[role])
        )

        assert response.status_code == 403

    def test_the_answer_is_the_version_as_it_will_be_read(
        self, client, world, team, wall, auth_header
    ):
        body = client.post(
            versions_url(world), json={"note": "v de prueba"}, headers=auth_header(team["lead"])
        ).json()

        assert (body["note"], body["total"], body["currency"]) == (
            "v de prueba",
            "3877800.00",
            "ARS",
        )
        assert [found["type"] for found in body["groups"]] == ["material", "labor", "equipment"]
        assert group(body, "equipment")["items"] == []
        assert body["created_by_name"] == "alba"
        assert body["prices_as_of"] is not None
        assert [line["quantity"] for line in body["lines"]] == ["120.000"]

    def test_saving_with_an_empty_take_off_is_a_409(self, client, world, team, auth_header):
        response = client.post(
            versions_url(world), json={"note": None}, headers=auth_header(team["lead"])
        )

        assert response.status_code == 409
        assert response.json()["detail"] == EMPTY_TAKEOFF

    def test_a_blank_note_is_stored_as_no_note(self, client, world, team, wall, auth_header):
        body = client.post(
            versions_url(world), json={"note": "   "}, headers=auth_header(team["lead"])
        ).json()

        assert body["note"] is None


class TestRead:
    @pytest.mark.parametrize("role", ["lead", "collaborator", "owner"])
    def test_these_roles_read_the_versions(self, client, world, team, version, auth_header, role):
        """The same four who may see the cost: reading a version adds no
        permission of its own (ADR-007 section 4)."""
        listing = client.get(versions_url(world), headers=auth_header(team[role]))
        detail = client.get(
            versions_url(world, version_id=version["id"]), headers=auth_header(team[role])
        )

        assert (listing.status_code, detail.status_code) == (200, 200)
        assert [row["version_number"] for row in listing.json()] == [1]

    @pytest.mark.parametrize("path", ["listing", "detail"])
    def test_the_client_does_not_see_the_versions(
        self, client, world, team, version, auth_header, path
    ):
        """HU-12, like HU-11: 403 and not 404, because they may see the work."""
        url = (
            versions_url(world)
            if path == "listing"
            else versions_url(world, version_id=version["id"])
        )

        assert client.get(url, headers=auth_header(team["client"])).status_code == 403

    def test_the_listing_is_newest_first(self, client, world, team, wall, auth_header):
        """By version number, which is what a person says out loud ("la v3")."""
        for _ in range(3):
            client.post(versions_url(world), json={"note": None}, headers=auth_header(team["lead"]))

        body = client.get(versions_url(world), headers=auth_header(team["lead"])).json()

        assert [row["version_number"] for row in body] == [3, 2, 1]

    def test_a_version_of_another_work_is_404(
        self, client, world, team, version, auth_header, new_project
    ):
        """Work A's version asked for under work B's URL. The firm filter alone
        would allow it, which is why the id of the work is asked for too."""
        other = new_project(world.firm_a, world.account_a, "Casa Segunda")

        response = client.get(
            versions_url(world, project_id=other, version_id=version["id"]),
            headers=auth_header(team["owner"]),
        )

        assert response.status_code == 404

    @pytest.mark.parametrize("role", ["bystander", "stranger"])
    def test_someone_off_the_work_gets_404(self, client, world, team, version, auth_header, role):
        assert client.get(versions_url(world), headers=auth_header(team[role])).status_code == 404

    def test_an_archived_work_is_404(self, client, db, world, team, version, auth_header):
        archive(db, world.project_a)

        assert client.get(versions_url(world), headers=auth_header(team["lead"])).status_code == 404


class TestMatchesTakeoff:
    """Which saved budget the work is standing on: the one whose lines are the
    take-off of today. Computed on every read, so each of these is a read."""

    def matching(self, client, world, team, auth_header) -> list[int]:
        body = client.get(versions_url(world), headers=auth_header(team["lead"])).json()
        return [row["version_number"] for row in body if row["matches_takeoff"]]

    def save(self, client, world, team, auth_header) -> dict:
        return client.post(
            versions_url(world), json={"note": None}, headers=auth_header(team["lead"])
        ).json()

    def test_a_version_just_saved_matches(self, client, world, team, version, auth_header):
        assert self.matching(client, world, team, auth_header) == [1]

    def test_a_new_line_leaves_no_version_matching(
        self, client, world, team, version, recipe_id, add_takeoff_line, auth_header
    ):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[SUBFLOOR], "40")

        assert self.matching(client, world, team, auth_header) == []

    def test_another_quantity_of_the_same_recipe_does_not_match(
        self, client, db, world, team, version, wall, auth_header
    ):
        db.execute(text("UPDATE project_recipe SET quantity = 121 WHERE id = :l"), {"l": wall})

        assert self.matching(client, world, team, auth_header) == []

    def test_another_note_on_the_same_line_does_not_match(
        self, client, db, world, team, version, wall, auth_header
    ):
        db.execute(text("UPDATE project_recipe SET note = 'PA' WHERE id = :l"), {"l": wall})

        assert self.matching(client, world, team, auth_header) == []

    def test_a_removed_line_is_not_part_of_the_take_off(
        self, client, world, team, version, recipe_id, add_takeoff_line, auth_header
    ):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[SUBFLOOR], "40", is_active=False)

        assert self.matching(client, world, team, auth_header) == [1]

    def test_two_equal_lines_are_not_one(
        self, client, world, team, version, recipe_id, add_takeoff_line, auth_header
    ):
        """The version froze one wall line; a second identical one is a change."""
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", note="PB")

        assert self.matching(client, world, team, auth_header) == []

    def test_saving_twice_without_changes_marks_both(
        self, client, world, team, version, auth_header
    ):
        self.save(client, world, team, auth_header)

        assert self.matching(client, world, team, auth_header) == [2, 1]

    def test_loading_an_older_version_moves_the_mark_to_it(
        self, client, world, team, version, recipe_id, add_takeoff_line, auth_header
    ):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[SUBFLOOR], "40")
        self.save(client, world, team, auth_header)
        assert self.matching(client, world, team, auth_header) == [2]

        client.post(
            f"{versions_url(world, version_id=version['id'])}/load",
            headers=auth_header(team["lead"]),
        )

        assert self.matching(client, world, team, auth_header) == [1]

    def test_a_price_change_does_not_unmark_a_version(
        self, client, db, world, team, version, auth_header
    ):
        """Same quantities at another price are still the same take-off."""
        db.execute(text("UPDATE resource SET reference_price = reference_price * 2"))

        assert self.matching(client, world, team, auth_header) == [1]

    def test_another_works_take_off_does_not_count(
        self, client, world, team, version, recipe_id, add_takeoff_line, auth_header
    ):
        add_takeoff_line(world.project_b, world.firm_b, recipe_id[SUBFLOOR], "40")

        assert self.matching(client, world, team, auth_header) == [1]


class TestLoad:
    def load_url(self, world, version_id: int) -> str:
        return f"{versions_url(world, version_id=version_id)}/load"

    @pytest.mark.parametrize("role", ["lead", "collaborator"])
    def test_these_roles_load_a_version(self, client, world, team, version, auth_header, role):
        response = client.post(self.load_url(world, version["id"]), headers=auth_header(team[role]))

        assert response.status_code == 200
        assert response.json() == {"loaded": 1, "skipped": []}

    @pytest.mark.parametrize("role", ["client", "owner"])
    def test_these_roles_cannot_load(self, client, world, team, version, auth_header, role):
        """Same permission as saving: replacing the draft is writing it."""
        response = client.post(self.load_url(world, version["id"]), headers=auth_header(team[role]))

        assert response.status_code == 403

    def test_a_retired_recipe_comes_back_as_a_skipped_name(
        self, client, db, world, team, wall, recipe_id, add_takeoff_line, auth_header
    ):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[SUBFLOOR], "50")
        saved = client.post(
            versions_url(world), json={"note": None}, headers=auth_header(team["lead"])
        ).json()
        db.execute(
            text("UPDATE recipe SET is_active = false WHERE id = :r"), {"r": recipe_id[SUBFLOOR]}
        )

        body = client.post(
            self.load_url(world, saved["id"]), headers=auth_header(team["lead"])
        ).json()

        assert body == {"loaded": 1, "skipped": [SUBFLOOR]}

    def test_loading_leaves_the_version_untouched(self, client, world, team, version, auth_header):
        client.post(self.load_url(world, version["id"]), headers=auth_header(team["lead"]))

        after = client.get(
            versions_url(world, version_id=version["id"]), headers=auth_header(team["lead"])
        ).json()
        assert after == version
