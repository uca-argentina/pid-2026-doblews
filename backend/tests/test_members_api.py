"""/firms/{firm_id}/members: the roster endpoints of HU-2.

The route audit in test_route_permissions.py already proves every one of these
declares a permission, resolves the roster, and answers an outsider with 404.
This file is about what each endpoint does for the people allowed in, and about
who is not.
"""

from datetime import datetime


def members_url(firm_id: int) -> str:
    return f"/firms/{firm_id}/members"


class TestListMembers:
    def test_the_owner_sees_the_roster_with_labels_and_state(self, client, world, auth_header):
        response = client.get(members_url(world.firm_a), headers=auth_header(world.account_a))

        assert response.status_code == 200
        body = response.json()
        # joined_at is set by the database, so it is checked for shape only.
        for member in body:
            datetime.fromisoformat(member.pop("joined_at"))
        assert body == [
            {
                "account_id": world.account_a2,
                "name": "alba",
                "email": "alba@test.com",
                "role": {"code": "architect", "name": "Arquitecto"},
                "is_active": True,
            },
            {
                "account_id": world.account_a,
                "name": "ana",
                "email": "ana@test.com",
                "role": {"code": "owner", "name": "Propietario"},
                "is_active": True,
            },
        ]

    def test_people_who_left_are_listed_as_inactive(self, client, world, auth_header, new_member):
        """HU-2's listing shows state, and the listing is where the owner finds
        someone to bring back."""
        gone = new_member(world.firm_a, "carla@test.com", "architect", is_active=False)

        body = client.get(members_url(world.firm_a), headers=auth_header(world.account_a)).json()

        assert {member["account_id"]: member["is_active"] for member in body}[gone] is False

    def test_an_architect_can_read_it(self, client, world, auth_header):
        """member.view: HU-3's client picker is filled from here, and architects
        create projects."""
        response = client.get(members_url(world.firm_a), headers=auth_header(world.account_a2))

        assert response.status_code == 200

    def test_a_firm_client_cannot(self, client, world, auth_header, new_member):
        """On the roster, so the firm exists for them: 403, not 404."""
        firm_client = new_member(world.firm_a, "cliente@test.com", "client")

        response = client.get(members_url(world.firm_a), headers=auth_header(firm_client))

        assert response.status_code == 403

    def test_someone_who_left_cannot_read_it_either(self, client, world, auth_header, new_member):
        """Leaving the roster closes this firm's door: 404, like any outsider."""
        gone = new_member(world.firm_a, "carla@test.com", "architect", is_active=False)

        response = client.get(members_url(world.firm_a), headers=auth_header(gone))

        assert response.status_code == 404

    def test_anonymous_gets_401(self, client, world):
        assert client.get(members_url(world.firm_a)).status_code == 401


class TestListMemberRoles:
    def test_offers_architect_and_client_with_their_seeded_labels(self, client, world, auth_header):
        response = client.get(
            f"{members_url(world.firm_a)}/roles", headers=auth_header(world.account_a)
        )

        assert response.status_code == 200
        assert response.json() == [
            {"code": "architect", "name": "Arquitecto"},
            {"code": "client", "name": "Cliente"},
        ]

    def test_an_architect_cannot_see_them(self, client, world, auth_header):
        """member.add: an architect cannot add anyone, so has no form to fill."""
        response = client.get(
            f"{members_url(world.firm_a)}/roles", headers=auth_header(world.account_a2)
        )

        assert response.status_code == 403
