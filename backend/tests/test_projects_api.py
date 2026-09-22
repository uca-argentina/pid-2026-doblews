"""The project endpoints, through HTTP (HU-3).

The rules themselves are pinned in test_project_service.py; what is under test
here is the border: which status code each situation gets, what the payload
looks like, and that no request reaches a work of another firm.

Ana owns firm A, Alba is an architect there, Bruno owns firm B. The world
fixture gives each firm one project, and nobody is assigned to either: that is
the starting point HU-3 describes, where an architect sees an empty listing
until they create something.
"""

import pytest
from sqlalchemy import text

from app.services.project import CLIENT_IS_NOT_A_CLIENT, CLIENT_NOT_ON_ROSTER

CASA = {"name": "Casa Nueva", "address": "Calle 1"}


@pytest.fixture
def clara(world, new_member):
    """A firm client of A, the one person the picker may offer."""
    return new_member(world.firm_a, "clara@test.com", "client")


def projects_url(firm_id: int, project_id: int | None = None) -> str:
    base = f"/firms/{firm_id}/projects"
    return base if project_id is None else f"{base}/{project_id}"


def create(client, world, auth_header, account_id, **fields):
    return client.post(
        projects_url(world.firm_a),
        json=CASA | fields,
        headers=auth_header(account_id),
    )


class TestCreate:
    def test_an_architect_creates_a_work_and_leads_it(self, client, world, auth_header, db):
        response = create(client, world, auth_header, world.account_a2)

        assert response.status_code == 201
        body = response.json()
        assert (body["name"], body["address"], body["client"]) == ("Casa Nueva", "Calle 1", None)

        role = db.execute(
            text("SELECT role_code FROM project_member WHERE project_id = :p"),
            {"p": body["id"]},
        ).scalar_one()
        assert role == "lead"

    def test_the_work_it_creates_is_its_own_firms(self, client, world, auth_header, db):
        """The firm comes from the URL, and the body has no say in it."""
        body = create(client, world, auth_header, world.account_a2).json()

        firm_id = db.execute(
            text("SELECT firm_id FROM project WHERE id = :p"), {"p": body["id"]}
        ).scalar_one()
        assert firm_id == world.firm_a

    def test_the_client_comes_back_on_the_response(self, client, world, auth_header, clara):
        body = create(client, world, auth_header, world.account_a2, client_account_id=clara).json()

        assert body["client"] == {"account_id": clara, "name": "clara"}

    def test_a_name_is_required(self, client, world, auth_header):
        response = client.post(
            projects_url(world.firm_a),
            json={"address": "Calle 1"},
            headers=auth_header(world.account_a2),
        )

        assert response.status_code == 422

    def test_a_blank_name_is_refused(self, client, world, auth_header):
        response = create(client, world, auth_header, world.account_a2, name="   ")

        assert response.status_code == 422

    def test_a_client_who_is_not_a_firm_client_is_a_conflict(self, client, world, auth_header):
        """409 and not 422: the body is well formed, it is the roster that
        refuses it."""
        response = create(
            client, world, auth_header, world.account_a2, client_account_id=world.account_a
        )

        assert response.status_code == 409
        assert response.json()["detail"] == CLIENT_IS_NOT_A_CLIENT

    def test_a_client_from_another_firm_is_a_conflict(self, client, world, auth_header):
        response = create(
            client, world, auth_header, world.account_a2, client_account_id=world.account_b
        )

        assert response.status_code == 409
        assert response.json()["detail"] == CLIENT_NOT_ON_ROSTER

    def test_a_firm_client_may_not_create_at_all(self, client, world, auth_header, clara):
        """403 from the guard, before any rule runs: a firm client does not hold
        project.create (ADR-002 section 7)."""
        response = create(client, world, auth_header, clara)

        assert response.status_code == 403

    def test_an_outsider_gets_404(self, client, world, auth_header):
        response = client.post(
            projects_url(world.firm_a), json=CASA, headers=auth_header(world.account_b)
        )

        assert response.status_code == 404


class TestListing:
    def test_a_creator_sees_the_work_it_created(self, client, world, auth_header):
        created = create(client, world, auth_header, world.account_a2).json()

        response = client.get(projects_url(world.firm_a), headers=auth_header(world.account_a2))

        assert response.status_code == 200
        assert [row["id"] for row in response.json()] == [created["id"]]

    def test_a_colleagues_work_is_not_listed(self, client, world, auth_header, new_member):
        """HU-3: "solo veo las obras del estudio activo donde soy miembro"."""
        other = new_member(world.firm_a, "andres@test.com", "architect")
        create(client, world, auth_header, world.account_a2)

        response = client.get(projects_url(world.firm_a), headers=auth_header(other))

        assert response.json() == []

    def test_the_owner_sees_every_work_of_the_firm(self, client, world, auth_header):
        """project.view_all, which is a row of the seed and not an `if owner`."""
        created = create(client, world, auth_header, world.account_a2).json()

        response = client.get(projects_url(world.firm_a), headers=auth_header(world.account_a))

        assert created["id"] in {row["id"] for row in response.json()}

    def test_the_owner_still_sees_nothing_of_another_firm(self, client, world, auth_header):
        response = client.get(projects_url(world.firm_a), headers=auth_header(world.account_a))

        assert world.project_b not in {row["id"] for row in response.json()}

    def test_the_listing_carries_what_hu3_asks_it_to_show(self, client, world, auth_header, clara):
        created = create(
            client,
            world,
            auth_header,
            world.account_a2,
            estimated_start_date="2026-10-15",
            client_account_id=clara,
        ).json()

        [row] = client.get(projects_url(world.firm_a), headers=auth_header(world.account_a2)).json()

        assert row == {
            "id": created["id"],
            "name": "Casa Nueva",
            "address": "Calle 1",
            "estimated_start_date": "2026-10-15",
            "client": {"account_id": clara, "name": "clara"},
        }

    def test_a_firm_client_gets_an_empty_listing_and_not_a_403(
        self, client, world, auth_header, clara
    ):
        """They hold firm.view like everyone, and the repository answers with
        the works they are on — none yet, until HU-6 assigns them."""
        response = client.get(projects_url(world.firm_a), headers=auth_header(clara))

        assert response.status_code == 200
        assert response.json() == []


class TestDetail:
    def test_a_member_of_the_work_reads_it(self, client, world, auth_header):
        created = create(client, world, auth_header, world.account_a2).json()

        response = client.get(
            projects_url(world.firm_a, created["id"]), headers=auth_header(world.account_a2)
        )

        assert response.status_code == 200
        assert response.json()["description"] is None

    def test_the_owner_reads_a_work_they_are_not_on(self, client, world, auth_header):
        """The case requires_any exists for: the owner has no project_member row,
        so only the firm-scope project.view_all can let them in."""
        created = create(client, world, auth_header, world.account_a2).json()

        response = client.get(
            projects_url(world.firm_a, created["id"]), headers=auth_header(world.account_a)
        )

        assert response.status_code == 200

    def test_a_colleagues_work_is_404_and_not_403(self, client, world, auth_header, new_member):
        """HU-3 is explicit: 404, "no revelamos que existe"."""
        other = new_member(world.firm_a, "andres@test.com", "architect")
        created = create(client, world, auth_header, world.account_a2).json()

        response = client.get(projects_url(world.firm_a, created["id"]), headers=auth_header(other))

        assert response.status_code == 404

    def test_another_firms_work_is_404(self, client, world, auth_header):
        """Asked for through firm A by Ana, who owns firm A and sees all of it."""
        response = client.get(
            projects_url(world.firm_a, world.project_b), headers=auth_header(world.account_a)
        )

        assert response.status_code == 404

    def test_a_work_that_does_not_exist_is_the_same_404(self, client, world, auth_header):
        response = client.get(
            projects_url(world.firm_a, 999999), headers=auth_header(world.account_a)
        )

        assert response.status_code == 404


class TestEdit:
    def saved(self, client, world, auth_header, account_id, project_id, **fields):
        return client.put(
            projects_url(world.firm_a, project_id),
            json=CASA | fields,
            headers=auth_header(account_id),
        )

    def test_the_lead_saves_the_form(self, client, world, auth_header):
        created = create(client, world, auth_header, world.account_a2).json()

        response = self.saved(
            client,
            world,
            auth_header,
            world.account_a2,
            created["id"],
            name="Casa Vieja",
            description="Reforma integral",
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Casa Vieja"
        assert response.json()["description"] == "Reforma integral"

    def test_a_field_left_out_of_the_body_is_cleared(self, client, world, auth_header):
        """PUT: the form sends the whole work, so no address means no address."""
        created = create(client, world, auth_header, world.account_a2).json()

        response = client.put(
            projects_url(world.firm_a, created["id"]),
            json={"name": "Casa Nueva"},
            headers=auth_header(world.account_a2),
        )

        assert response.json()["address"] is None

    def test_the_client_is_set_and_then_cleared(self, client, world, auth_header, clara):
        created = create(client, world, auth_header, world.account_a2).json()

        with_client = self.saved(
            client, world, auth_header, world.account_a2, created["id"], client_account_id=clara
        )
        assert with_client.json()["client"]["account_id"] == clara

        without = self.saved(client, world, auth_header, world.account_a2, created["id"])
        assert without.json()["client"] is None

    def test_an_architect_cannot_be_the_client(self, client, world, auth_header):
        created = create(client, world, auth_header, world.account_a2).json()

        response = self.saved(
            client,
            world,
            auth_header,
            world.account_a2,
            created["id"],
            client_account_id=world.account_a,
        )

        assert response.status_code == 409

    def test_the_owner_may_read_it_but_not_edit_it(self, client, world, auth_header):
        """403 and not 404: project.view_all makes the work visible to Ana, so
        hiding it would protect nothing. What she lacks is project.edit, which
        only the works's own roles grant."""
        created = create(client, world, auth_header, world.account_a2).json()

        response = self.saved(client, world, auth_header, world.account_a, created["id"])

        assert response.status_code == 403

    def test_a_colleague_gets_404(self, client, world, auth_header, new_member):
        other = new_member(world.firm_a, "andres@test.com", "architect")
        created = create(client, world, auth_header, world.account_a2).json()

        response = self.saved(client, world, auth_header, other, created["id"])

        assert response.status_code == 404


class TestArchive:
    def test_the_lead_archives_it(self, client, world, auth_header):
        created = create(client, world, auth_header, world.account_a2).json()

        response = client.delete(
            projects_url(world.firm_a, created["id"]), headers=auth_header(world.account_a2)
        )

        assert response.status_code == 204
        assert response.content == b""

    def test_it_leaves_the_listing_and_its_detail_answers_404(self, client, world, auth_header):
        created = create(client, world, auth_header, world.account_a2).json()
        client.delete(
            projects_url(world.firm_a, created["id"]), headers=auth_header(world.account_a2)
        )

        listing = client.get(projects_url(world.firm_a), headers=auth_header(world.account_a2))
        detail = client.get(
            projects_url(world.firm_a, created["id"]), headers=auth_header(world.account_a2)
        )

        assert listing.json() == []
        assert detail.status_code == 404

    def test_the_row_is_still_in_the_database(self, client, world, auth_header, db):
        """Baja lógica: nothing is deleted, is_active is flipped."""
        created = create(client, world, auth_header, world.account_a2).json()
        client.delete(
            projects_url(world.firm_a, created["id"]), headers=auth_header(world.account_a2)
        )

        active = db.execute(
            text("SELECT is_active FROM project WHERE id = :p"), {"p": created["id"]}
        ).scalar_one()
        assert active is False

    def test_the_owner_may_not_archive_someone_elses_work(self, client, world, auth_header):
        created = create(client, world, auth_header, world.account_a2).json()

        response = client.delete(
            projects_url(world.firm_a, created["id"]), headers=auth_header(world.account_a)
        )

        assert response.status_code == 403


class TestWhatTheCallerMayDo:
    """The detail says what this person may do to this work, for painting.

    It is what lets the screen offer "Editar" and "Dar de baja" only when they
    would be accepted, the same way the sidebar hides a section the caller has
    no permission for.
    """

    def detail(self, client, world, auth_header, account_id, project_id):
        return client.get(
            projects_url(world.firm_a, project_id), headers=auth_header(account_id)
        ).json()

    def test_the_lead_may_edit_and_archive(self, client, world, auth_header):
        created = create(client, world, auth_header, world.account_a2).json()

        body = self.detail(client, world, auth_header, world.account_a2, created["id"])

        assert {"project.edit", "project.archive"} <= set(body["permissions"])

    def test_the_owner_of_the_firm_may_do_nothing_to_a_work_they_are_not_on(
        self, client, world, auth_header
    ):
        """The case this field exists for. Ana sees every work of her firm
        through project.view_all, and ADR-002 section 7 gives her no project
        role on this one, so the screen must offer her no actions."""
        created = create(client, world, auth_header, world.account_a2).json()

        body = self.detail(client, world, auth_header, world.account_a, created["id"])

        assert body["permissions"] == []

    def test_the_codes_come_back_sorted(self, client, world, auth_header):
        """So the payload does not reshuffle between two identical requests."""
        created = create(client, world, auth_header, world.account_a2).json()

        body = self.detail(client, world, auth_header, world.account_a2, created["id"])

        assert body["permissions"] == sorted(body["permissions"])

    def test_the_listing_does_not_carry_them(self, client, world, auth_header):
        """There is no project_id in its path to resolve project permissions
        against, which is why the actions of a work live on its own screen."""
        create(client, world, auth_header, world.account_a2)

        [row] = client.get(projects_url(world.firm_a), headers=auth_header(world.account_a2)).json()

        assert "permissions" not in row

    def test_a_write_answers_without_them(self, client, world, auth_header):
        """A write answers before there is anything to paint; the screen reads
        the detail again afterwards."""
        created = create(client, world, auth_header, world.account_a2)

        assert "permissions" not in created.json()
