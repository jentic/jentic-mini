"""Alembic migration environment for Jentic Mini.

Runs raw-SQL migrations against the SQLite database at DB_PATH.
No SQLAlchemy ORM models — all migrations use op.execute().
"""
from logging.config import fileConfig

from sqlalchemy import create_engine, inspect, pool, text

from alembic import context

from src.config import DB_PATH

# Alembic Config object
config = context.config

# Set up Python logging from .ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No SQLAlchemy models — raw SQL migrations only
target_metadata = None

# Build SQLAlchemy URL from the app's DB_PATH config
db_url = f"sqlite:///{DB_PATH}"


def _auto_stamp_pre_alembic_db(connection):
    """Detect a pre-Alembic database and stamp it at the baseline revision.

    If the database has tables (e.g. 'apis') but no 'alembic_version' table,
    it was created before the Alembic migration. Stamp it at '0001' so the
    baseline migration is skipped.
    """
    inspector = inspect(connection)
    tables = inspector.get_table_names()
    if "alembic_version" not in tables and "apis" in tables:
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        connection.execute(text("INSERT INTO alembic_version VALUES ('0001')"))
        connection.commit()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the live database."""
    connectable = create_engine(db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        # Enable SQLite foreign keys
        connection.execute(text("PRAGMA foreign_keys = ON"))

        # Auto-stamp pre-Alembic databases
        _auto_stamp_pre_alembic_db(connection)

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        # SQLite auto-commits DDL, so the version stamp may be in a
        # separate implicit transaction. Ensure it's flushed.
        connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
