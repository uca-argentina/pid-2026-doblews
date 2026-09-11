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
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.core.token import create_access_token
from app.db.session import get_db
from app.main import app

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


def _clear_leftover_rows(url: sa.URL) -> None:
    """Empty the test database before the migrations run down.

    The catalogue migration's downgrade deletes the roles it seeded, so a single
    stray platform_member row pointing at one makes it fail on a foreign key.
    That surfaces as every test in the suite erroring during setup, with a
    message naming neither the cause nor the fix.

    Rows only get here by accident — a seed script aimed at the wrong database,
    a run killed mid-test — but this database exists to be thrown away, so
    clearing it is always safe and costs less than diagnosing it by hand.

    Read from the database rather than from Base.metadata, so a table left over
    by a half-applied migration is cleared too. alembic_version is left alone:
    the downgrade needs to know where it is starting from.
    """
    engine = sa.create_engine(url)
    with engine.begin() as connection:
        tables = [
            name for name in sa.inspect(connection).get_table_names() if name != "alembic_version"
        ]
        if tables:
            quoted = ", ".join(f'"{name}"' for name in tables)
            connection.execute(text(f"TRUNCATE {quoted} CASCADE"))
    engine.dispose()


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
    _clear_leftover_rows(url)

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
def new_project(db: Connection):
    """Another project besides the world's two, active or archived."""

    def _new(firm_id: int, created_by: int, name: str, is_active: bool = True) -> int:
        return db.execute(
            text(
                "INSERT INTO project (firm_id, name, created_by, is_active)"
                " VALUES (:f, :n, :c, :a) RETURNING id"
            ),
            {"f": firm_id, "n": name, "c": created_by, "a": is_active},
        ).scalar_one()

    return _new


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


# The password every account in the API tests answers to.
TEST_PASSWORD = "test-password"


@pytest.fixture(scope="session")
def password_hash() -> str:
    """Hashed once for the whole run, not once per test.

    bcrypt is slow by design — around 250 ms a call — so hashing per test would
    make this file the slowest thing in the suite for no added coverage.
    """
    return hash_password(TEST_PASSWORD)


@pytest.fixture
def db_session(db: Connection) -> Iterator[Session]:
    """An ORM Session on the test's own connection, for testing services directly.

    The db fixture hands out a raw Connection because the oldest tests here are
    about what the database refuses. Service functions take a Session, so this
    wraps the same connection in one: both see the same rows and both are undone
    by the same rollback.
    """
    session = Session(bind=db, autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db: Connection) -> Iterator[TestClient]:
    """A TestClient whose endpoints run on the test's own connection.

    Without the override the app would open its own connections against the
    development database: the rows this test inserted would be invisible to the
    endpoint, and anything the endpoint wrote would outlive the test.

    A Session per request, exactly as in production. Binding it to a Connection
    that already has a transaction open makes SQLAlchemy 2.0 open a SAVEPOINT
    instead of a second transaction (join_transaction_mode defaults to
    "conditional_savepoint"), so a commit inside a request cannot escape the
    rollback in the db fixture. The 1.3-era recipe of nesting transactions by
    hand and re-opening them from an after_transaction_end listener is not only
    unnecessary here, it breaks this.
    """

    def override_get_db() -> Iterator[Session]:
        session = Session(bind=db, autoflush=False, expire_on_commit=False)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    # pop and not clear(): another fixture may be overriding something else.
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def usable_passwords(db: Connection, password_hash: str) -> str:
    """Give every seeded account a real hash, and return the password.

    The world fixture stores 'not-a-real-hash' on purpose, since its own tests
    are about what the database refuses. Logging in needs something bcrypt can
    actually verify.
    """
    db.execute(text("UPDATE account SET password_hash = :hash"), {"hash": password_hash})
    return TEST_PASSWORD


@pytest.fixture
def auth_header():
    """account id -> the Authorization header for it, signed for real."""

    def _header(account_id: int) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(account_id)}"}

    return _header
