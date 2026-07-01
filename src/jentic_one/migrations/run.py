"""Programmatic Alembic migration runner.

Runs ``alembic upgrade`` for one or more databases without relying on the
repo-root ``alembic.ini`` or a particular working directory. This is the
entry point used by the deployment migration Job (``python -m
jentic_one.migrations.run``) so the same packaged code that ships in the
service image also applies schema migrations.

The runner builds an Alembic :class:`~alembic.config.Config` in memory,
pointing ``script_location`` at the packaged ``migrations`` directory and
``version_locations`` at the per-database ``versions`` folder. Database URLs
and target schemas are resolved by the existing ``env.py`` from application
config (``JENTIC__DATABASES__*`` env vars), so there is a single source of
truth for connection details.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from jentic_one.migrations.targets import DB_METADATA

VALID_DBS: tuple[str, ...] = tuple(DB_METADATA.keys())

_MIGRATIONS_DIR = Path(__file__).resolve().parent


def _build_config(db_name: str) -> Config:
    """Construct an in-memory Alembic config for a single database section."""
    cfg = Config()
    cfg.config_ini_section = db_name
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    cfg.set_main_option("version_locations", str(_MIGRATIONS_DIR / db_name / "versions"))
    cfg.set_main_option("path_separator", "os")
    return cfg


def upgrade(db_name: str, target: str = "head") -> None:
    """Apply migrations for a single database up to ``target``."""
    if db_name not in VALID_DBS:
        raise ValueError(f"Unknown database {db_name!r}; expected one of {VALID_DBS}")
    cfg = _build_config(db_name)
    command.upgrade(cfg, target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply Alembic migrations.")
    parser.add_argument(
        "--db",
        action="append",
        choices=VALID_DBS,
        help="Database to migrate (repeatable). Defaults to all databases.",
    )
    parser.add_argument(
        "--target",
        default="head",
        help="Target revision (default: head).",
    )
    args = parser.parse_args(argv)

    databases = args.db or list(VALID_DBS)
    for db_name in databases:
        print(f"==> Migrating {db_name} to {args.target}", flush=True)
        upgrade(db_name, args.target)
        print(f"==> {db_name} complete", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
