"""Backfill scheme blob for the jentic-mini self-credential.

The jentic-mini credential is created at startup by _ensure_internal_credential.
Previously it had no pre-computed scheme blob because derive_scheme_for_credential
would try to load the self-spec — which may not exist yet at the time the credential
is created. From startup.py v0.7.3+ the scheme is passed explicitly; this migration
backfills the one existing row so the DB is consistent and
get_merged_security_schemes can be removed from the broker entirely.

Revision ID: 0005
Revises: 0004
"""

import json
from alembic import op
from sqlalchemy import text

revision = "0005"
down_revision = "0004"


def upgrade() -> None:
    scheme = json.dumps({"in": "header", "name": "X-Jentic-API-Key"})
    op.execute(
        text("UPDATE credentials SET scheme=:scheme WHERE id='jentic-mini' AND scheme IS NULL").bindparams(scheme=scheme)
    )


def downgrade() -> None:
    op.execute(
        text("UPDATE credentials SET scheme=NULL WHERE id='jentic-mini'")
    )
