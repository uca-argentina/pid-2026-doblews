"""Alembic entry point: wires the migration runner to this project.

Tells Alembic which database to run against and what the schema should look like
according to the models, which is what makes autogenerate and `alembic check` work.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base

# Importing app.models above is load-bearing, not a stray import: it is what
# registers every table on Base.metadata. Without it autogenerate compares the
# database against an empty schema and writes a migration that drops everything.

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve the database to migrate.

    Programmatic callers (the test suite) pass their own URL through
    config.attributes; everything else uses the app settings. We cannot read it
    from alembic.ini instead, because that file still holds the template
    placeholder and there would be no way to tell a real value from it.
    """
    return config.attributes.get("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Emits SQL to stdout instead of running it, for reviewing a migration or
    handing it to a DBA. No database connection is opened.
    """
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database.

    NullPool because a migration run is a short-lived process: pooling
    connections it is about to throw away buys nothing.
    """
    connectable = create_engine(get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
