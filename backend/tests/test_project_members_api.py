"""/firms/{firm_id}/projects/{project_id}/members: the team endpoints of HU-6.

The route audit in test_route_permissions.py already proves every one of these
declares a permission, resolves the roster, and answers an outsider with 404.
This file is about what each endpoint does for the people allowed in, and about
who is not — which for a team section is most of the story, since the difference
between a lead and a collaborator is exactly what it exists to enforce.
"""

from datetime import datetime

import pytest
from sqlalchemy import text

from app.api.deps import FORBIDDEN, PROJECT_NOT_FOUND
from app.api.routes.project_members import TEAM_MEMBER_NOT_FOUND
from app.services.project_team import (
    ALREADY_HAS_CLIENT,
    ALREADY_ON_TEAM,
    CANNOT_LEAVE_AS_LEAD,
    FIRM_CLIENT_ONLY_AS_CLIENT,
    LEAD_IS_TRANSFERRED,
    NOT_ON_ROSTER,
)


def team_url(firm_id: int, project_id: int) -> str:
    return f"/firms/{firm_id}/projects/{project_id}/members"


@pytest.fixture
def led_by_ana(world, add_project_member):
    """Firm A's work with Ana leading it: the caller of nearly every test here."""
    add_project_member(world.project_a, world.account_a, world.firm_a, "lead")


class TestListTeam:
    def test_the_lead_sees_the_team_with_labels_and_state(
        self, client, world, auth_header, led_by_ana, add_project_member
    ):
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")

        response = client.get(
            team_url(world.firm_a, world.project_a), headers=auth_header(world.account_a)
        )

        assert response.status_code == 200
        body = response.json()
        # joined_at is set by the database, so it is checked for shape only.
        for member in body:
            datetime.fromisoformat(member.pop("joined_at"))
        # The lead first, then by name: that is the order the section renders.
        assert body == [
            {
                "account_id": world.account_a,
                "name": "ana",
                "email": "ana@test.com",
                "role": {"code": "lead", "name": "Responsable"},
                "is_active": True,
            },
            {
                "account_id": world.account_a2,
                "name": "alba",
                "email": "alba@test.com",
                "role": {"code": "collaborator", "name": "Colaborador"},
                "is_active": True,
            },
        ]

    def test_a_collaborator_sees_the_team_too(
        self, client, world, auth_header, led_by_ana, add_project_member
    ):
        """HU-6: they see it and cannot change it. project.member.view is theirs."""
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")

        response = client.get(
            team_url(world.firm_a, world.project_a), headers=auth_header(world.account_a2)
        )

        assert response.status_code == 200

    def test_someone_who_left_the_firm_is_listed_as_inactive(
        self, client, world, auth_header, led_by_ana, new_member, add_project_member, db
    ):
        """Their seat is still theirs and comes back with them (ADR-002 section
        11.3); until then the section says so rather than hiding it."""
        gone = new_member(world.firm_a, "carla@test.com", "architect")
        add_project_member(world.project_a, gone, world.firm_a, "collaborator")
        db.execute(
            text("UPDATE firm_member SET is_active = false WHERE account_id = :a"), {"a": gone}
        )

        body = client.get(
            team_url(world.firm_a, world.project_a), headers=auth_header(world.account_a)
        ).json()

        assert [(m["account_id"], m["is_active"]) for m in body] == [
            (world.account_a, True),
            (gone, False),
        ]

    def test_the_client_of_the_work_may_not_see_the_team(
        self, client, world, auth_header, led_by_ana, new_member, add_project_member
    ):
        """ADR-002 section 7 gives the project client project.view and nothing
        else: who else works on the studio's side is not part of what they see."""
        cleo = new_member(world.firm_a, "cleo@test.com", "client")
        add_project_member(world.project_a, cleo, world.firm_a, "client")

        response = client.get(team_url(world.firm_a, world.project_a), headers=auth_header(cleo))

        assert response.status_code == 403
        assert response.json()["detail"] == FORBIDDEN

    def test_the_firm_owner_who_is_not_on_the_work_gets_403(
        self, client, world, auth_header, add_project_member
    ):
        """project.view_all opens the work, and is not a project.member.*
        permission. A 403 and not a 404, because they can already see the work
        exists — the detail screen simply does not paint the tab for them."""
        add_project_member(world.project_a, world.account_a2, world.firm_a, "lead")

        response = client.get(
            team_url(world.firm_a, world.project_a), headers=auth_header(world.account_a)
        )

        assert response.status_code == 403

    def test_a_member_of_the_firm_who_is_not_on_the_work_gets_404(
        self, client, world, auth_header, led_by_ana
    ):
        """Alba is an architect of firm A without project.view_all: the work is
        invisible to her, so it cannot be a 403."""
        response = client.get(
            team_url(world.firm_a, world.project_a), headers=auth_header(world.account_a2)
        )

        assert response.status_code == 404

    def test_an_archived_work_answers_404(
        self, client, world, auth_header, new_project, add_project_member
    ):
        """Its team is untouched in the database, and unreachable like the work."""
        archived = new_project(world.firm_a, world.account_a, "Casa Vieja", is_active=False)
        add_project_member(archived, world.account_a, world.firm_a, "lead")

        response = client.get(
            team_url(world.firm_a, archived), headers=auth_header(world.account_a)
        )

        assert response.status_code == 404
        assert response.json()["detail"] == PROJECT_NOT_FOUND


class TestAddMember:
    def test_the_lead_puts_someone_from_the_roster_on_the_work(
        self, client, world, auth_header, led_by_ana
    ):
        response = client.post(
            team_url(world.firm_a, world.project_a),
            json={"account_id": world.account_a2, "role_code": "collaborator"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 201
        body = response.json()
        assert (body["account_id"], body["role"]["code"], body["is_active"]) == (
            world.account_a2,
            "collaborator",
            True,
        )

    def test_a_collaborator_may_not(
        self, client, world, auth_header, led_by_ana, add_project_member, new_member
    ):
        """HU-6: the controls do not appear, and calling the endpoint anyway is a 403."""
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")
        carla = new_member(world.firm_a, "carla@test.com", "architect")

        response = client.post(
            team_url(world.firm_a, world.project_a),
            json={"account_id": carla, "role_code": "collaborator"},
            headers=auth_header(world.account_a2),
        )

        assert response.status_code == 403

    def test_someone_from_another_firm_is_a_409_and_not_a_silent_success(
        self, client, world, auth_header, led_by_ana
    ):
        """HU-6: the picker never offers them, and the endpoint refuses them too."""
        response = client.post(
            team_url(world.firm_a, world.project_a),
            json={"account_id": world.account_b, "role_code": "collaborator"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == NOT_ON_ROSTER

    def test_a_firm_client_is_refused_any_role_but_client(
        self, client, world, auth_header, led_by_ana, new_member
    ):
        cleo = new_member(world.firm_a, "cleo@test.com", "client")

        response = client.post(
            team_url(world.firm_a, world.project_a),
            json={"account_id": cleo, "role_code": "collaborator"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == FIRM_CLIENT_ONLY_AS_CLIENT

    def test_a_second_client_is_refused(
        self, client, world, auth_header, led_by_ana, new_member, add_project_member
    ):
        first = new_member(world.firm_a, "cleo@test.com", "client")
        second = new_member(world.firm_a, "dario@test.com", "client")
        add_project_member(world.project_a, first, world.firm_a, "client")

        response = client.post(
            team_url(world.firm_a, world.project_a),
            json={"account_id": second, "role_code": "client"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == ALREADY_HAS_CLIENT

    def test_someone_already_on_the_team_is_refused(
        self, client, world, auth_header, led_by_ana, add_project_member
    ):
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")

        response = client.post(
            team_url(world.firm_a, world.project_a),
            json={"account_id": world.account_a2, "role_code": "collaborator"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == ALREADY_ON_TEAM

    def test_a_firm_role_code_is_refused_before_any_code_runs(
        self, client, world, auth_header, led_by_ana
    ):
        """architect is a firm role. The Literal makes it a 422, not a 409."""
        response = client.post(
            team_url(world.firm_a, world.project_a),
            json={"account_id": world.account_a2, "role_code": "architect"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 422

    def test_assigning_lead_transfers_it_in_one_request(
        self, client, world, auth_header, led_by_ana
    ):
        response = client.post(
            team_url(world.firm_a, world.project_a),
            json={"account_id": world.account_a2, "role_code": "lead"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 201
        # Read back through the API, which is now Alba's to read: Ana was demoted
        # to collaborator and still holds project.member.view.
        body = client.get(
            team_url(world.firm_a, world.project_a), headers=auth_header(world.account_a2)
        ).json()
        assert {m["account_id"]: m["role"]["code"] for m in body} == {
            world.account_a: "collaborator",
            world.account_a2: "lead",
        }


class TestChangeRole:
    def test_the_lead_changes_someone_else_s_role(
        self, client, world, auth_header, led_by_ana, add_project_member
    ):
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")

        response = client.patch(
            f"{team_url(world.firm_a, world.project_a)}/{world.account_a2}",
            json={"role_code": "client"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 200
        assert response.json()["role"] == {"code": "client", "name": "Cliente"}

    def test_the_lead_cannot_be_moved_off_the_lead_role(
        self, client, world, auth_header, led_by_ana
    ):
        response = client.patch(
            f"{team_url(world.firm_a, world.project_a)}/{world.account_a}",
            json={"role_code": "collaborator"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == LEAD_IS_TRANSFERRED

    def test_somebody_not_on_the_team_is_a_404(self, client, world, auth_header, led_by_ana):
        response = client.patch(
            f"{team_url(world.firm_a, world.project_a)}/{world.account_a2}",
            json={"role_code": "collaborator"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == TEAM_MEMBER_NOT_FOUND

    def test_a_collaborator_may_not(
        self, client, world, auth_header, led_by_ana, add_project_member, new_member
    ):
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")
        carla = new_member(world.firm_a, "carla@test.com", "architect")
        add_project_member(world.project_a, carla, world.firm_a, "collaborator")

        response = client.patch(
            f"{team_url(world.firm_a, world.project_a)}/{carla}",
            json={"role_code": "client"},
            headers=auth_header(world.account_a2),
        )

        assert response.status_code == 403


class TestRemoveMember:
    def test_the_lead_takes_someone_off_the_work(
        self, client, world, auth_header, led_by_ana, add_project_member
    ):
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")

        response = client.delete(
            f"{team_url(world.firm_a, world.project_a)}/{world.account_a2}",
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 204
        body = client.get(
            team_url(world.firm_a, world.project_a), headers=auth_header(world.account_a)
        ).json()
        assert [m["account_id"] for m in body] == [world.account_a]

    def test_whoever_is_taken_off_stops_seeing_the_work_at_once(
        self, client, world, auth_header, led_by_ana, add_project_member
    ):
        """HU-6: "quien queda fuera deja de ver la obra inmediatamente". Permissions
        are resolved against the database on every request, never from the token."""
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")
        header = auth_header(world.account_a2)
        assert (
            client.get(team_url(world.firm_a, world.project_a), headers=header).status_code == 200
        )

        client.delete(
            f"{team_url(world.firm_a, world.project_a)}/{world.account_a2}",
            headers=auth_header(world.account_a),
        )

        # The same token, still perfectly valid, now finds nothing.
        assert (
            client.get(team_url(world.firm_a, world.project_a), headers=header).status_code == 404
        )

    def test_the_lead_cannot_take_themselves_off(self, client, world, auth_header, led_by_ana):
        response = client.delete(
            f"{team_url(world.firm_a, world.project_a)}/{world.account_a}",
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == CANNOT_LEAVE_AS_LEAD


class TestListRoles:
    def test_the_lead_gets_the_three_roles_with_their_labels(
        self, client, world, auth_header, led_by_ana
    ):
        response = client.get(
            f"{team_url(world.firm_a, world.project_a)}/roles",
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 200
        assert response.json() == [
            {"code": "client", "name": "Cliente"},
            {"code": "collaborator", "name": "Colaborador"},
            {"code": "lead", "name": "Responsable"},
        ]

    def test_a_collaborator_may_not_read_them(
        self, client, world, auth_header, led_by_ana, add_project_member
    ):
        """They sit behind manage, like HU-2's equivalent: only the screens that
        assign need them."""
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")

        response = client.get(
            f"{team_url(world.firm_a, world.project_a)}/roles",
            headers=auth_header(world.account_a2),
        )

        assert response.status_code == 403
