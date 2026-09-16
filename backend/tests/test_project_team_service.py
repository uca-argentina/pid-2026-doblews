"""The rules of changing a work's team (HU-6).

Against the session directly, without HTTP: what is under test is the rule and
the transaction, not the status code it eventually becomes. The API tests cover
that half.

The invariant that matters most here is the one HU-6 states twice — "la obra
nunca se queda sin responsable ni con dos" — so most of this file is about the
lead seat: that it transfers rather than being vacated, and that there is never
a moment with a different number of leads than one.
"""

import pytest
from sqlalchemy import text

from app.models import Project
from app.services.project_team import (
    ALREADY_HAS_CLIENT,
    ALREADY_ON_TEAM,
    CANNOT_LEAVE_AS_LEAD,
    FIRM_CLIENT_ONLY_AS_CLIENT,
    LEAD_IS_TRANSFERRED,
    NOT_ON_ROSTER,
    ProjectTeamError,
    TeamMemberNotFoundError,
    add_team_member,
    change_team_role,
    list_assignable_roles,
    remove_team_member,
)


def team(db_session, project_id: int) -> dict[int, str]:
    """account_id -> role_code, read straight from the table."""
    rows = db_session.execute(
        text("SELECT account_id, role_code FROM project_member WHERE project_id = :p"),
        {"p": project_id},
    ).all()
    return {row.account_id: row.role_code for row in rows}


@pytest.fixture
def project(db_session, world) -> Project:
    """Firm A's work, led by Ana. The starting point of nearly every test here."""
    db_session.execute(
        text(
            "INSERT INTO project_member"
            " (project_id, account_id, firm_id, role_id, role_scope, role_code)"
            " SELECT :p, :a, :f, id, 'project', 'lead' FROM role"
            " WHERE code = 'lead' AND scope = 'project'"
        ),
        {"p": world.project_a, "a": world.account_a, "f": world.firm_a},
    )
    db_session.flush()
    return db_session.get(Project, world.project_a)


class TestAdd:
    def test_puts_a_member_of_the_roster_on_the_work(self, db_session, world, project):
        add_team_member(db_session, project, account_id=world.account_a2, role_code="collaborator")

        assert team(db_session, project.id) == {
            world.account_a: "lead",
            world.account_a2: "collaborator",
        }

    def test_refuses_someone_who_is_not_on_the_roster(self, db_session, world, project):
        """Bruno belongs to firm B. Nothing about him is firm A's to assign."""
        with pytest.raises(ProjectTeamError) as refused:
            add_team_member(db_session, project, account_id=world.account_b, role_code="viewer")

        assert refused.value.detail == NOT_ON_ROSTER
        assert team(db_session, project.id) == {world.account_a: "lead"}

    def test_refuses_someone_who_left_the_roster(self, db_session, world, project, new_member):
        """ADR-002 section 2: the firm layer is the door to the project layer, so
        the row would grant nothing."""
        gone = new_member(world.firm_a, "carla@test.com", "architect", is_active=False)

        with pytest.raises(ProjectTeamError) as refused:
            add_team_member(db_session, project, account_id=gone, role_code="collaborator")

        assert refused.value.detail == NOT_ON_ROSTER

    def test_refuses_someone_already_on_the_team(self, db_session, world, project):
        add_team_member(db_session, project, account_id=world.account_a2, role_code="viewer")

        with pytest.raises(ProjectTeamError) as refused:
            add_team_member(db_session, project, account_id=world.account_a2, role_code="viewer")

        assert refused.value.detail == ALREADY_ON_TEAM

    def test_a_firm_client_may_only_be_the_client(self, db_session, world, project, new_member):
        """ADR-002 section 11.2, and HU-6: the picker does not even offer the rest."""
        cleo = new_member(world.firm_a, "cleo@test.com", "client")

        with pytest.raises(ProjectTeamError) as refused:
            add_team_member(db_session, project, account_id=cleo, role_code="collaborator")

        assert refused.value.detail == FIRM_CLIENT_ONLY_AS_CLIENT

    def test_a_firm_client_may_be_the_client(self, db_session, world, project, new_member):
        cleo = new_member(world.firm_a, "cleo@test.com", "client")

        add_team_member(db_session, project, account_id=cleo, role_code="client")

        assert team(db_session, project.id)[cleo] == "client"

    def test_refuses_a_second_client(self, db_session, world, project, new_member):
        """HU-6 allows at most one, and says nothing about transferring it: an
        outgoing client cannot be demoted anywhere, so replacing them silently
        would throw them off the work."""
        first = new_member(world.firm_a, "cleo@test.com", "client")
        second = new_member(world.firm_a, "dario@test.com", "client")
        add_team_member(db_session, project, account_id=first, role_code="client")

        with pytest.raises(ProjectTeamError) as refused:
            add_team_member(db_session, project, account_id=second, role_code="client")

        assert refused.value.detail == ALREADY_HAS_CLIENT
        assert team(db_session, project.id)[first] == "client"

    def test_adding_a_lead_transfers_it(self, db_session, world, project):
        """The whole point of HU-6's lead rule: one in, one demoted, never two."""
        add_team_member(db_session, project, account_id=world.account_a2, role_code="lead")

        assert team(db_session, project.id) == {
            world.account_a: "collaborator",
            world.account_a2: "lead",
        }


class TestChangeRole:
    def test_changes_the_role_on_the_work(self, db_session, world, project):
        add_team_member(db_session, project, account_id=world.account_a2, role_code="collaborator")

        change_team_role(
            db_session,
            project,
            actor_id=world.account_a,
            account_id=world.account_a2,
            role_code="viewer",
        )

        assert team(db_session, project.id)[world.account_a2] == "viewer"

    def test_asking_for_the_role_they_already_hold_changes_nothing(
        self, db_session, world, project
    ):
        """A double-submitted form is harmless."""
        add_team_member(db_session, project, account_id=world.account_a2, role_code="viewer")

        change_team_role(
            db_session,
            project,
            actor_id=world.account_a,
            account_id=world.account_a2,
            role_code="viewer",
        )

        assert team(db_session, project.id)[world.account_a2] == "viewer"

    def test_refuses_moving_the_lead_off_the_lead_role(self, db_session, world, project):
        """The one way to leave a work with nobody responsible."""
        with pytest.raises(ProjectTeamError) as refused:
            change_team_role(
                db_session,
                project,
                actor_id=world.account_a,
                account_id=world.account_a,
                role_code="collaborator",
            )

        assert refused.value.detail == LEAD_IS_TRANSFERRED
        assert team(db_session, project.id) == {world.account_a: "lead"}

    def test_promoting_someone_to_lead_transfers_it(self, db_session, world, project):
        add_team_member(db_session, project, account_id=world.account_a2, role_code="viewer")

        change_team_role(
            db_session,
            project,
            actor_id=world.account_a,
            account_id=world.account_a2,
            role_code="lead",
        )

        assert team(db_session, project.id) == {
            world.account_a: "collaborator",
            world.account_a2: "lead",
        }

    def test_refuses_someone_who_is_not_on_the_team(self, db_session, world, project):
        with pytest.raises(TeamMemberNotFoundError):
            change_team_role(
                db_session,
                project,
                actor_id=world.account_a,
                account_id=world.account_a2,
                role_code="viewer",
            )

    def test_refuses_when_the_person_left_the_roster(self, db_session, world, project, new_member):
        """Their seat is inert; promoting them to lead would leave the work with a
        responsible who cannot open it."""
        gone = new_member(world.firm_a, "carla@test.com", "architect")
        add_team_member(db_session, project, account_id=gone, role_code="collaborator")
        db_session.execute(
            text("UPDATE firm_member SET is_active = false WHERE account_id = :a"), {"a": gone}
        )

        with pytest.raises(ProjectTeamError) as refused:
            change_team_role(
                db_session, project, actor_id=world.account_a, account_id=gone, role_code="lead"
            )

        assert refused.value.detail == NOT_ON_ROSTER
        assert team(db_session, project.id)[world.account_a] == "lead"


class TestRemove:
    def test_takes_someone_off_the_work(self, db_session, world, project):
        add_team_member(db_session, project, account_id=world.account_a2, role_code="collaborator")

        remove_team_member(
            db_session, project, actor_id=world.account_a, account_id=world.account_a2
        )

        assert team(db_session, project.id) == {world.account_a: "lead"}

    def test_the_lead_cannot_take_themselves_off(self, db_session, world, project):
        """HU-6: "No puedo quitarme a mí mismo si soy el único lead" — and with one
        lead per work, the only lead is the lead."""
        with pytest.raises(ProjectTeamError) as refused:
            remove_team_member(
                db_session, project, actor_id=world.account_a, account_id=world.account_a
            )

        assert refused.value.detail == CANNOT_LEAVE_AS_LEAD
        assert team(db_session, project.id) == {world.account_a: "lead"}

    def test_nobody_else_can_take_the_lead_off_either(self, db_session, world, project):
        with pytest.raises(ProjectTeamError) as refused:
            remove_team_member(
                db_session, project, actor_id=world.account_a2, account_id=world.account_a
            )

        assert refused.value.detail == LEAD_IS_TRANSFERRED

    def test_refuses_someone_who_is_not_on_the_team(self, db_session, world, project):
        with pytest.raises(TeamMemberNotFoundError):
            remove_team_member(
                db_session, project, actor_id=world.account_a, account_id=world.account_a2
            )


class TestAssignableRoles:
    def test_offers_the_four_project_roles_with_their_seeded_labels(self, db_session):
        """Read from the seed, so the frontend keeps no dictionary of its own."""
        roles = {role.code: role.name for role in list_assignable_roles(db_session)}

        assert roles == {
            "lead": "Responsable",
            "collaborator": "Colaborador",
            "viewer": "Lector",
            "client": "Cliente",
        }
