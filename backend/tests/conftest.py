"""Test fixtures: a throwaway database built by the real migrations.

Applies Alembic to TEST_DATABASE_URL once per session so tests meet the actual
triggers, CHECKs and seeded catalogue, then wraps each test in a rolled-back
transaction so they cannot see each other's rows.
"""

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import make_url

from alembic import command
from alembic.config import Config
from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _create_database_if_missing(url: sa.URL) -> None:
    """CREATE DATABASE cannot run inside a transaction, hence AUTOCOMMIT.

    Connects to the `postgres` maintenance database, which always exists, to ask
    about and create the one we actually want.
    """
    admin = sa.create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """The test database, built by the migrations themselves.

    Deliberately not Base.metadata.create_all: the trigger, the CHECKs and the
    permission catalogue only exist in migrations, so a schema built any other
    way would not be the schema that reaches production.
    """
    settings = get_settings()
    if not settings.test_database_url:
        pytest.fail("TEST_DATABASE_URL is not set. Copy the line from .env.example into your .env")

    url = make_url(settings.test_database_url)
    _create_database_if_missing(url)

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    # The channel alembic/env.py reads, so the suite never touches DATABASE_URL.
    config.attributes["sqlalchemy.url"] = settings.test_database_url
    # Down first: every run starts clean and exercises the downgrade path, which
    # is the half nobody notices is broken until they need it.
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = sa.create_engine(settings.test_database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Connection]:
    """One transaction per test, always rolled back.

    A raw Connection rather than an ORM session on purpose: these tests are about
    what the database refuses, and the ORM would only stand in the way.
    """
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


@pytest.fixture
def role_id(db: Connection) -> dict[tuple[str, str], int]:
    """(code, scope) -> id for the seeded roles."""
    return {
        (row.code, row.scope): row.id
        for row in db.execute(text("SELECT id, code, scope FROM role"))
    }


@pytest.fixture
def permission_id(db: Connection) -> dict[tuple[str, str], int]:
    """(code, scope) -> id for the seeded permissions."""
    return {
        (row.code, row.scope): row.id
        for row in db.execute(text("SELECT id, code, scope FROM permission"))
    }


@pytest.fixture
def world(db: Connection, role_id: dict[tuple[str, str], int]) -> SimpleNamespace:
    """Two firms that must never see each other, each with a roster and a project.

    Named a and b so the isolation tests read as plain sentences: "put b's person
    into a's project", "point a's membership at b's project".
    """

    def new_firm(name: str) -> int:
        return db.execute(
            text("INSERT INTO firm (name, contact_email) VALUES (:n, :e) RETURNING id"),
            {"n": name, "e": f"{name}@test.com"},
        ).scalar_one()

    def new_account(email: str) -> int:
        return db.execute(
            text(
                "INSERT INTO account (name, email, password_hash)"
                " VALUES (:n, :e, 'not-a-real-hash') RETURNING id"
            ),
            {"n": email.split("@")[0], "e": email},
        ).scalar_one()

    def add_to_roster(firm: int, account: int, code: str) -> None:
        db.execute(
            text(
                "INSERT INTO firm_member (firm_id, account_id, role_id, role_scope)"
                " VALUES (:f, :a, :r, 'firm')"
            ),
            {"f": firm, "a": account, "r": role_id[(code, "firm")]},
        )

    def new_project(firm: int, created_by: int, name: str) -> int:
        return db.execute(
            text(
                "INSERT INTO project (firm_id, name, created_by) VALUES (:f, :n, :c) RETURNING id"
            ),
            {"f": firm, "n": name, "c": created_by},
        ).scalar_one()

    firm_a = new_firm("norte")
    firm_b = new_firm("sur")

    # Two people in firm A, so "only one lead per project" has a second candidate.
    account_a = new_account("ana@test.com")
    account_a2 = new_account("alba@test.com")
    account_b = new_account("bruno@test.com")

    add_to_roster(firm_a, account_a, "owner")
    add_to_roster(firm_a, account_a2, "architect")
    add_to_roster(firm_b, account_b, "owner")

    return SimpleNamespace(
        firm_a=firm_a,
        firm_b=firm_b,
        account_a=account_a,
        account_a2=account_a2,
        account_b=account_b,
        project_a=new_project(firm_a, account_a, "Casa Norte"),
        project_b=new_project(firm_b, account_b, "Casa Sur"),
    )


@pytest.fixture
def add_project_member(db: Connection, role_id: dict[tuple[str, str], int]):
    """Insert one project_member row, spelling out every column it ties together."""

    def _add(project: int, account: int, firm: int, code: str) -> None:
        db.execute(
            text(
                "INSERT INTO project_member"
                " (project_id, account_id, firm_id, role_id, role_scope, role_code)"
                " VALUES (:p, :a, :f, :r, :s, :c)"
            ),
            {
                "p": project,
                "a": account,
                "f": firm,
                "r": role_id[(code, "project")],
                "s": "project",
                "c": code,
            },
        )

    return _add
