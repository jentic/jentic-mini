"""add search embeddings (historical no-op)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-10

This migration originally created the pgvector extension and added
``search_embedding vector(384)`` columns to ``operations`` and ``api_revisions``.
Semantic/pgvector search has since been removed in favour of lexical
(full-text / BM25) search, and the ``vector_variant`` column type and the
``pgvector`` dependency no longer exist. Rewriting this revision as a pure
no-op keeps ``alembic upgrade head`` working on fresh installs (it can no
longer import the deleted type), while later migrations own the lexical
``search_text`` column and its indexes. Existing databases that already ran
the original version have their embedding columns dropped by the
``add_lexical_search_text`` migration.
"""

from collections.abc import Sequence

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op: pgvector semantic search was removed."""


def downgrade() -> None:
    """No-op: pgvector semantic search was removed."""
