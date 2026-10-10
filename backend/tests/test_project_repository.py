"""Which project rows a read returns — the second level of enforcement.

ADR-002 section 8: "Un permiso no salva de un WHERE olvidado." These tests are
about the WHERE, so most of them pass the permission set in by hand rather than
resolving it: what is under test is the query, not the catalogue.

The last class is about the other half of the read, the client HU-3's listing
shows beside each project: who it is, and when it is nobody.
"""

import pytest

from app.repositories.base import FirmScopedRepository
from app.repositories.project import VIEW_ALL, ProjectRepository
from app.services.auth import get_firm_membership
from app.services.authz import firm_permissions

MEMBER_ONLY = frozenset()
SEES_EVERYTHING = frozenset({VIEW_ALL})


def repo(db_session, firm_id: int) -> ProjectRepository:
    return ProjectRepository(db_session, firm_id=firm_id)


def ids(entries) -> set[int]:
    return {entry.project.id for entry in entries}


class TestMembership:
    def test_a_member_sees_the_project_they_are_on(self, db_session, world, add_project_member):
        add_project_member(world.project_a, world.account_a, world.firm_a, "lead")

        found = repo(db_session, world.firm_a).list_entries(world.account_a, MEMBER_ONLY)

        assert ids(found) == {world.project_a}

    def test_belonging_to_the_firm_is_not_belonging_to_its_projects(self, db_session, world):
        """Ana is on firm_a's roster and on no project of it. HU-3: "solo veo las
        obras del estudio activo donde soy miembro"."""
        found = repo(db_session, world.firm_a).list_entries(world.account_a, MEMBER_ONLY)

        assert found == []

    def test_projects_come_back_in_name_order(
        self, db_session, world, new_project, add_project_member
    ):
        for name in ("Zulema", "Alfa"):
            project_id = new_project(world.firm_a, world.account_a, name)
            add_project_member(project_id, world.account_a, world.firm_a, "collaborator")

        found = repo(db_session, world.firm_a).list_entries(world.account_a, MEMBER_ONLY)

        assert [entry.project.name for entry in found] == ["Alfa", "Zulema"]


class TestViewAll:
    def test_view_all_returns_projects_the_caller_is_not_on(self, db_session, world, new_project):
        """The permission is firm-scope, and it changes which project rows come
        back. That is why an endpoint guard cannot do this job."""
        other = new_project(world.firm_a, world.account_a, "Casa ajena")

        found = repo(db_session, world.firm_a).list_entries(world.account_a, SEES_EVERYTHING)

        assert ids(found) == {world.project_a, other}

    def test_view_all_still_stops_at_the_firm_boundary(self, db_session, world):
        """The strongest project permission in the catalogue, and it still does
        not reach across tenants: that is section 8's whole point."""
        found = repo(db_session, world.firm_a).list_entries(world.account_a, SEES_EVERYTHING)

        assert world.project_b not in ids(found)

    def test_the_owner_really_holds_it(self, db_session, world, new_project):
        """The one case that goes through the catalogue instead of a literal set,
        so the seed and this query are shown to agree."""
        membership = get_firm_membership(
            db_session, account_id=world.account_a, firm_id=world.firm_a
        )
        assert membership is not None
        granted = firm_permissions(db_session, membership.role_id)
        other = new_project(world.firm_a, world.account_a, "Casa ajena")

        found = repo(db_session, world.firm_a).list_entries(world.account_a, granted)

        assert ids(found) == {world.project_a, other}

    def test_the_architect_does_not(self, db_session, world):
        membership = get_firm_membership(
            db_session, account_id=world.account_a2, firm_id=world.firm_a
        )
        assert membership is not None
        granted = firm_permissions(db_session, membership.role_id)

        found = repo(db_session, world.firm_a).list_entries(world.account_a2, granted)

        assert found == []


class TestArchived:
    def test_an_archived_project_is_gone_even_for_view_all(self, db_session, world, new_project):
        """Logical deletion, filtered in the base select so no caller can forget."""
        new_project(world.firm_a, world.account_a, "Obra vieja", is_active=False)

        found = repo(db_session, world.firm_a).list_entries(world.account_a, SEES_EVERYTHING)

        assert ids(found) == {world.project_a}


class TestGetVisible:
    def test_returns_a_project_the_caller_may_see(self, db_session, world, add_project_member):
        add_project_member(world.project_a, world.account_a, world.firm_a, "collaborator")

        found = repo(db_session, world.firm_a).get_visible(
            world.project_a, world.account_a, MEMBER_ONLY
        )

        assert found is not None and found.id == world.project_a

    def test_another_firms_project_is_none(self, db_session, world):
        """Asked for through firm_a, which is the only firm this caller proved."""
        assert (
            repo(db_session, world.firm_a).get_visible(
                world.project_b, world.account_a, SEES_EVERYTHING
            )
            is None
        )

    def test_a_project_of_this_firm_the_caller_is_not_on_is_none(self, db_session, world):
        assert (
            repo(db_session, world.firm_a).get_visible(
                world.project_a, world.account_a, MEMBER_ONLY
            )
            is None
        )

    def test_a_project_that_does_not_exist_is_none(self, db_session, world):
        """Same None as the two above, so the endpoint answers all of them with
        the same 404 and never confirms which case it was."""
        assert (
            repo(db_session, world.firm_a).get_visible(999999, world.account_a, SEES_EVERYTHING)
            is None
        )


class TestTheClient:
    """HU-3's listing shows the client of each work, and ADR-002 section 6 says
    there is nowhere to read it from but project_member."""

    def only(self, db_session, world):
        [entry] = repo(db_session, world.firm_a).list_entries(world.account_a, SEES_EVERYTHING)
        return entry

    def test_a_project_with_no_client_says_so(self, db_session, world):
        """The field may stay empty (HU-3), so this is the ordinary case and not
        an error: the project comes back, with nobody beside it."""
        assert self.only(db_session, world).client is None

    def test_the_client_comes_back_with_their_name(
        self, db_session, world, new_member, add_project_member
    ):
        client = new_member(world.firm_a, "clara@test.com", "client")
        add_project_member(world.project_a, client, world.firm_a, "client")

        found = self.only(db_session, world).client

        assert found is not None
        assert (found.account_id, found.name) == (client, "clara")

    def test_the_rest_of_the_team_is_not_mistaken_for_the_client(
        self, db_session, world, add_project_member
    ):
        """A lead and a collaborator are project_member rows too. Only the one
        holding role_code = 'client' is the client."""
        add_project_member(world.project_a, world.account_a, world.firm_a, "lead")
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")

        assert self.only(db_session, world).client is None

    def test_the_project_is_listed_once_however_big_its_team(
        self, db_session, world, new_member, add_project_member
    ):
        """The join must not multiply rows: a work with a lead, a collaborator
        and a client is still one line in the listing."""
        client = new_member(world.firm_a, "clara@test.com", "client")
        add_project_member(world.project_a, world.account_a, world.firm_a, "lead")
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")
        add_project_member(world.project_a, client, world.firm_a, "client")

        found = repo(db_session, world.firm_a).list_entries(world.account_a, SEES_EVERYTHING)

        assert len(found) == 1
        assert found[0].client is not None and found[0].client.account_id == client

    def test_a_client_who_left_the_roster_is_not_shown(
        self, db_session, world, new_member, add_project_member
    ):
        """Their assignment is inert, not deleted (ADR-002 section 11.3), so the
        project stays and only the name stops being printed."""
        gone = new_member(world.firm_a, "clara@test.com", "client", is_active=False)
        add_project_member(world.project_a, gone, world.firm_a, "client")

        entry = self.only(db_session, world)

        assert entry.project.id == world.project_a
        assert entry.client is None

    def test_the_caller_seeing_it_through_membership_still_gets_the_client(
        self, db_session, world, new_member, add_project_member
    ):
        """The two joins to project_member are different rows and must not be
        confused: here the caller is the lead and somebody else is the client."""
        client = new_member(world.firm_a, "clara@test.com", "client")
        add_project_member(world.project_a, world.account_a, world.firm_a, "lead")
        add_project_member(world.project_a, client, world.firm_a, "client")

        [entry] = repo(db_session, world.firm_a).list_entries(world.account_a, MEMBER_ONLY)

        assert entry.client is not None and entry.client.account_id == client


class TestEntry:
    def test_returns_the_project_with_its_client(
        self, db_session, world, new_member, add_project_member
    ):
        client = new_member(world.firm_a, "clara@test.com", "client")
        add_project_member(world.project_a, client, world.firm_a, "client")

        entry = repo(db_session, world.firm_a).entry(
            world.project_a, world.account_a, SEES_EVERYTHING
        )

        assert entry is not None
        assert entry.project.id == world.project_a
        assert entry.client is not None and entry.client.account_id == client

    def test_another_firms_project_is_none(self, db_session, world):
        assert (
            repo(db_session, world.firm_a).entry(world.project_b, world.account_a, SEES_EVERYTHING)
            is None
        )

    def test_a_project_of_this_firm_the_caller_is_not_on_is_none(self, db_session, world):
        assert (
            repo(db_session, world.firm_a).entry(world.project_a, world.account_a, MEMBER_ONLY)
            is None
        )


def test_a_repository_cannot_scope_a_table_without_a_tenant():
    """account has no firm_id on purpose: it is the global identity, so one
    person can belong to several firms. Scoping it would be meaningless, and the
    class refuses to be defined rather than silently returning everything."""
    from app.models import Account

    with pytest.raises(TypeError, match="no firm_id"):

        class Accounts(FirmScopedRepository[Account]):
            model = Account
