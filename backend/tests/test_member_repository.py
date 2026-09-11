"""Which roster rows a read returns, and what a member holds in the firm's projects.

The world fixture gives firm_a two people (ana, owner; alba, architect) and firm_b
one (bruno, owner). Tests that need a person in both firms put alba in firm_b as
well, since isolation is only proved by someone who could leak across.
"""

import pytest
from sqlalchemy import text

from app.repositories.member import FirmMemberRepository


def repo(db_session, firm_id: int) -> FirmMemberRepository:
    return FirmMemberRepository(db_session, firm_id=firm_id)


@pytest.fixture
def leave_roster(db):
    def _leave(firm_id: int, account_id: int) -> None:
        db.execute(
            text("UPDATE firm_member SET is_active = false WHERE firm_id = :f AND account_id = :a"),
            {"f": firm_id, "a": account_id},
        )

    return _leave


@pytest.fixture
def alba(world) -> int:
    """firm_a's architect: the member whose project roles the rules ask about."""
    return world.account_a2


@pytest.fixture
def alba_also_in_firm_b(world, join_roster):
    """Alba joins firm_b as an architect: one person on two rosters."""
    join_roster(world.firm_b, world.account_a2, "architect")


class TestListRoster:
    def test_lists_this_firms_members_with_their_labels(self, db_session, world):
        entries = repo(db_session, world.firm_a).list_roster()

        assert [
            (entry.account_id, entry.name, entry.email, entry.role_code, entry.role_name)
            for entry in entries
        ] == [
            (world.account_a2, "alba", "alba@test.com", "architect", "Arquitecto"),
            (world.account_a, "ana", "ana@test.com", "owner", "Propietario"),
        ]
        assert all(entry.is_active for entry in entries)

    def test_another_firms_members_are_never_listed(self, db_session, world):
        entries = repo(db_session, world.firm_b).list_roster()

        assert [entry.account_id for entry in entries] == [world.account_b]

    def test_people_who_left_are_listed_after_the_active_ones(
        self, db_session, world, leave_roster
    ):
        """Alba sorts first by name, and still comes last once she has left."""
        leave_roster(world.firm_a, world.account_a2)

        entries = repo(db_session, world.firm_a).list_roster()

        assert [(entry.account_id, entry.is_active) for entry in entries] == [
            (world.account_a, True),
            (world.account_a2, False),
        ]

    def test_leaving_one_roster_does_not_list_you_as_gone_from_another(
        self, db_session, world, leave_roster, alba_also_in_firm_b
    ):
        leave_roster(world.firm_a, world.account_a2)

        entries = repo(db_session, world.firm_b).list_roster()

        assert {entry.account_id: entry.is_active for entry in entries}[world.account_a2] is True


class TestGet:
    def test_returns_an_active_member(self, db_session, world):
        found = repo(db_session, world.firm_a).get(world.account_a2)

        assert found is not None
        assert (found.firm_id, found.account_id) == (world.firm_a, world.account_a2)

    def test_a_member_of_another_firm_is_none(self, db_session, world):
        assert repo(db_session, world.firm_a).get(world.account_b) is None

    def test_someone_who_left_is_none_unless_asked_for(self, db_session, world, leave_roster):
        leave_roster(world.firm_a, world.account_a2)
        members = repo(db_session, world.firm_a)

        assert members.get(world.account_a2) is None
        found = members.get(world.account_a2, include_inactive=True)
        assert found is not None and found.is_active is False


class TestBaseSelect:
    """include_inactive is new in the base, so the base is re-proved here: the
    default still hides logically deleted rows, and the opt-out drops that filter
    and only that one."""

    def test_the_default_still_hides_inactive_rows(self, db_session, world, leave_roster):
        leave_roster(world.firm_a, world.account_a2)
        members = repo(db_session, world.firm_a)

        found = {member.account_id for member in db_session.scalars(members.select())}

        assert found == {world.account_a}

    def test_including_inactive_rows_never_widens_the_tenant(self, db_session, world, leave_roster):
        leave_roster(world.firm_b, world.account_b)
        members = repo(db_session, world.firm_a)

        found = {
            (member.firm_id, member.account_id)
            for member in db_session.scalars(members.select(include_inactive=True))
        }

        assert found == {(world.firm_a, world.account_a), (world.firm_a, world.account_a2)}

    def test_the_opt_out_cannot_be_passed_by_position(self, db_session, world):
        """Keyword-only, so dropping the filter is always visible at the call site."""
        with pytest.raises(TypeError):
            repo(db_session, world.firm_a).select(True)


class TestNonClientProjectRoles:
    def test_no_project_roles_at_all(self, db_session, world, alba):
        assert repo(db_session, world.firm_a).has_non_client_project_roles(alba) is False

    def test_being_a_client_on_a_project_is_not_a_conflict(
        self, db_session, world, alba, add_project_member
    ):
        add_project_member(world.project_a, alba, world.firm_a, "client")

        assert repo(db_session, world.firm_a).has_non_client_project_roles(alba) is False

    @pytest.mark.parametrize("code", ["lead", "collaborator", "viewer"])
    def test_any_other_project_role_is(self, db_session, world, alba, add_project_member, code):
        add_project_member(world.project_a, alba, world.firm_a, code)

        assert repo(db_session, world.firm_a).has_non_client_project_roles(alba) is True

    def test_an_archived_project_still_counts(
        self, db_session, world, alba, new_project, add_project_member
    ):
        archived = new_project(world.firm_a, world.account_a, "Obra vieja", is_active=False)
        add_project_member(archived, alba, world.firm_a, "collaborator")

        assert repo(db_session, world.firm_a).has_non_client_project_roles(alba) is True

    def test_another_firms_projects_do_not_count(
        self, db_session, world, alba, add_project_member, alba_also_in_firm_b
    ):
        add_project_member(world.project_b, alba, world.firm_b, "lead")

        assert repo(db_session, world.firm_a).has_non_client_project_roles(alba) is False
        assert repo(db_session, world.firm_b).has_non_client_project_roles(alba) is True


class TestLeadsActiveProjects:
    def test_the_lead_of_a_live_project(self, db_session, world, alba, add_project_member):
        add_project_member(world.project_a, alba, world.firm_a, "lead")

        assert repo(db_session, world.firm_a).leads_active_projects(alba) is True

    def test_another_role_on_the_same_project_is_not_leading(
        self, db_session, world, alba, add_project_member
    ):
        add_project_member(world.project_a, alba, world.firm_a, "collaborator")

        assert repo(db_session, world.firm_a).leads_active_projects(alba) is False

    def test_leading_an_archived_project_does_not_count(
        self, db_session, world, alba, new_project, add_project_member
    ):
        archived = new_project(world.firm_a, world.account_a, "Obra vieja", is_active=False)
        add_project_member(archived, alba, world.firm_a, "lead")

        assert repo(db_session, world.firm_a).leads_active_projects(alba) is False

    def test_leading_in_another_firm_does_not_count(
        self, db_session, world, alba, add_project_member, alba_also_in_firm_b
    ):
        add_project_member(world.project_b, alba, world.firm_b, "lead")

        assert repo(db_session, world.firm_a).leads_active_projects(alba) is False
        assert repo(db_session, world.firm_b).leads_active_projects(alba) is True
