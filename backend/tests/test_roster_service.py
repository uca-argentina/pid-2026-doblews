"""The roster rules of HU-2, tested on the service without HTTP in the way.

The world fixture gives firm_a ana (owner) and alba (architect), and firm_b bruno
(owner). Bruno is the person "who already has an account because they work with
another firm" that HU-2 is written around.
"""

import pytest
from sqlalchemy import select, text

from app.core.security import verify_password
from app.models import Account, FirmMember
from app.services.authz import project_permissions
from app.services.roster import (
    ALREADY_MEMBER,
    CLIENT_WITH_PROJECT_ROLES,
    STAFF_ACCOUNT,
    RosterError,
    add_member,
)

TYPED_PASSWORD = "clave-inicial"


def add(db_session, firm_id: int, email: str, role_code: str = "architect", name: str = "Nueva"):
    return add_member(
        db_session,
        firm_id,
        name=name,
        email=email,
        role_code=role_code,
        password=TYPED_PASSWORD,
    )


@pytest.fixture
def support_account(db, role_id) -> int:
    account_id = db.execute(
        text(
            "INSERT INTO account (name, email, password_hash)"
            " VALUES ('Soporte', 'soporte@test.com', 'not-a-real-hash') RETURNING id"
        )
    ).scalar_one()
    db.execute(
        text(
            "INSERT INTO platform_member (account_id, role_id, role_scope)"
            " VALUES (:a, :r, 'platform')"
        ),
        {"a": account_id, "r": role_id[("support", "platform")]},
    )
    return account_id


class TestNewAccount:
    def test_creates_the_account_with_the_typed_name_and_password(self, db_session, world):
        member = add(db_session, world.firm_a, "nueva@test.com", name="Nueva Persona")

        account = db_session.get(Account, member.account_id)
        assert account is not None
        assert (account.name, account.email) == ("Nueva Persona", "nueva@test.com")
        assert verify_password(TYPED_PASSWORD, account.password_hash)

    def test_puts_it_on_the_roster_with_the_chosen_role(self, db_session, world, role_id):
        member = add(db_session, world.firm_a, "nueva@test.com", role_code="client")

        assert member.firm_id == world.firm_a
        assert member.is_active is True
        assert member.role_id == role_id[("client", "firm")]


class TestExistingAccount:
    """Bruno already has an account: he owns firm_b."""

    def test_no_second_account_is_created(self, db_session, world):
        member = add(db_session, world.firm_a, "bruno@test.com")

        assert member.account_id == world.account_b
        accounts = db_session.scalars(select(Account).where(Account.email == "bruno@test.com"))
        assert len(accounts.all()) == 1

    def test_his_name_and_password_are_left_alone(self, db_session, world):
        before = db_session.get(Account, world.account_b)
        assert before is not None
        name, password_hash = before.name, before.password_hash

        add(db_session, world.firm_a, "bruno@test.com", name="Otro Nombre")

        after = db_session.get(Account, world.account_b)
        assert after is not None
        assert (after.name, after.password_hash) == (name, password_hash)

    def test_joining_a_second_firm_leaves_the_first_alone(self, db_session, world):
        add(db_session, world.firm_a, "bruno@test.com")

        in_b = db_session.get(FirmMember, (world.firm_b, world.account_b))
        assert in_b is not None and in_b.is_active is True

    def test_an_active_member_cannot_be_added_twice(self, db_session, world):
        with pytest.raises(RosterError) as refused:
            add(db_session, world.firm_a, "alba@test.com")

        assert refused.value.detail == ALREADY_MEMBER

    def test_platform_staff_cannot_join_a_firm(self, db_session, world, support_account):
        with pytest.raises(RosterError) as refused:
            add(db_session, world.firm_a, "soporte@test.com")

        assert refused.value.detail == STAFF_ACCOUNT
        assert db_session.get(FirmMember, (world.firm_a, support_account)) is None


class TestReinstating:
    """Carla worked in firm_a and left. Adding her again is how she comes back."""

    @pytest.fixture
    def carla(self, world, new_member) -> int:
        return new_member(world.firm_a, "carla@test.com", "architect", is_active=False)

    def test_her_row_comes_back_with_the_new_role(self, db_session, world, role_id, carla):
        before = db_session.get(FirmMember, (world.firm_a, carla))
        assert before is not None
        joined_at = before.joined_at

        member = add(db_session, world.firm_a, "carla@test.com", role_code="client")

        assert (member.account_id, member.is_active) == (carla, True)
        assert member.role_id == role_id[("client", "firm")]
        assert member.joined_at == joined_at

    def test_her_projects_come_back_on_their_own(
        self, db_session, world, add_project_member, carla
    ):
        """ADR-002 section 11.3: the assignments were inert, never deleted."""
        add_project_member(world.project_a, carla, world.firm_a, "lead")
        assert project_permissions(db_session, carla, world.project_a, world.firm_a) == frozenset()

        add(db_session, world.firm_a, "carla@test.com")

        assert "project.edit" in project_permissions(
            db_session, carla, world.project_a, world.firm_a
        )

    def test_she_cannot_come_back_as_a_client_while_leading_a_project(
        self, db_session, world, add_project_member, carla
    ):
        add_project_member(world.project_a, carla, world.firm_a, "lead")

        with pytest.raises(RosterError) as refused:
            add(db_session, world.firm_a, "carla@test.com", role_code="client")

        assert refused.value.detail == CLIENT_WITH_PROJECT_ROLES
        member = db_session.get(FirmMember, (world.firm_a, carla))
        assert member is not None and member.is_active is False

    def test_she_can_come_back_as_a_client_if_she_was_one_on_the_project(
        self, db_session, world, add_project_member, carla
    ):
        add_project_member(world.project_a, carla, world.firm_a, "client")

        member = add(db_session, world.firm_a, "carla@test.com", role_code="client")

        assert member.is_active is True
