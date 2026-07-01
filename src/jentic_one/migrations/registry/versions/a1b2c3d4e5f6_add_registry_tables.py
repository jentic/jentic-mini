"""add registry tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-06-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from jentic_one.shared.db.types import GUID, json_variant, string_array_variant, text_array_variant

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"
    uuid_default = sa.func.gen_random_uuid() if pg else None

    if pg:
        op.execute("""
            CREATE OR REPLACE FUNCTION generate_ksuid(prefix text) RETURNS text
            LANGUAGE sql VOLATILE
            AS $$
                SELECT prefix || '_' ||
                    lpad(to_hex(extract(epoch FROM clock_timestamp())::bigint), 8, '0') ||
                    substr(replace(gen_random_uuid()::text, '-', ''), 1, 16)
            $$
        """)

    op.create_table(
        "apis",
        sa.Column(
            "id",
            GUID(),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("vendor", sa.String(100), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon_url", sa.String(2048), nullable=True),
        sa.Column("current_revision_id", GUID(), nullable=True),
        sa.Column("revision_count", sa.Integer, server_default=sa.text("0"), nullable=False),
        sa.Column("operation_count", sa.Integer, server_default=sa.text("0"), nullable=False),
        sa.Column("revision", sa.Integer, server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vendor", "name", "version", name="uq_apis_vendor_name_version"),
    )
    op.create_index("ix_apis_vendor", "apis", ["vendor"])
    op.create_index("ix_apis_vendor_name", "apis", ["vendor", "name"])
    op.create_index("ix_apis_created_at", "apis", ["created_at"])
    op.create_index("ix_apis_created_by", "apis", ["created_by"])

    op.create_table(
        "api_revisions",
        sa.Column(
            "id",
            GUID(),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("api_id", GUID(), nullable=False),
        sa.Column("state", sa.String(20), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("spec_digest", sa.String(100), nullable=True),
        sa.Column("source_type", sa.String(20), nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("source_filename", sa.String(512), nullable=True),
        sa.Column("source_content_id", GUID(), nullable=True),
        sa.Column("submitted_by", sa.String(255), nullable=True),
        sa.Column("operation_count", sa.Integer, server_default=sa.text("0"), nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["api_id"], ["apis.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("api_id", "spec_digest", name="uq_api_revisions_api_id_spec_digest"),
    )
    op.create_index("ix_api_revisions_api_id", "api_revisions", ["api_id"])
    op.create_index("ix_api_revisions_created_at", "api_revisions", ["created_at"])
    op.create_index("ix_api_revisions_created_by", "api_revisions", ["created_by"])
    op.create_index(
        "ix_api_revisions_one_published",
        "api_revisions",
        ["api_id"],
        unique=True,
        postgresql_where=sa.text("state = 'published'"),
        sqlite_where=sa.text("state = 'published'"),
    )

    # Deferred FK: apis.current_revision_id -> api_revisions.id
    if pg:
        op.create_foreign_key(
            "fk_apis_current_revision_id",
            "apis",
            "api_revisions",
            ["current_revision_id"],
            ["id"],
        )
    else:
        with op.batch_alter_table("apis") as batch:
            batch.create_foreign_key(
                "fk_apis_current_revision_id",
                "api_revisions",
                ["current_revision_id"],
                ["id"],
            )

    op.create_table(
        "spec_files",
        sa.Column(
            "id",
            GUID(),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("revision_id", GUID(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content", json_variant(), nullable=False),
        sa.Column("sha", sa.String(64), nullable=True),
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["revision_id"], ["api_revisions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("revision_id", "filename", name="uq_spec_files_revision_id_filename"),
    )
    op.create_index("ix_spec_files_revision_id", "spec_files", ["revision_id"])
    op.create_index("ix_spec_files_source_id", "spec_files", ["source_id"])
    op.create_index("ix_spec_files_created_at", "spec_files", ["created_at"])
    op.create_index("ix_spec_files_created_by", "spec_files", ["created_by"])

    op.create_table(
        "operations",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("revision_id", GUID(), nullable=False),
        sa.Column("operation_id", sa.String(255), nullable=True),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("summary", sa.String(500), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tags", string_array_variant(), nullable=True),
        sa.Column("deprecated", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("raw_operation", json_variant(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["revision_id"], ["api_revisions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "revision_id", "path", "method", name="uq_operations_revision_path_method"
        ),
        sa.UniqueConstraint(
            "revision_id", "operation_id", name="uq_operations_revision_operation_id"
        ),
    )
    op.create_index("ix_operations_revision_id", "operations", ["revision_id"])
    op.create_index("ix_operations_operation_id", "operations", ["operation_id"])
    op.create_index("ix_operations_created_at", "operations", ["created_at"])
    op.create_index("ix_operations_created_by", "operations", ["created_by"])
    # GIN index is Postgres-only; on SQLite the tags JSON column is left unindexed.
    if pg:
        op.create_index("ix_operations_tags", "operations", ["tags"], postgresql_using="gin")

    op.create_table(
        "servers",
        sa.Column(
            "id",
            GUID(),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("revision_id", GUID(), nullable=False),
        sa.Column("operation_id", sa.String(50), nullable=True),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["revision_id"], ["api_revisions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_servers_revision_id", "servers", ["revision_id"])
    op.create_index("ix_servers_operation_id", "servers", ["operation_id"])
    op.create_index("ix_servers_created_at", "servers", ["created_at"])
    op.create_index("ix_servers_created_by", "servers", ["created_by"])

    # Deferred FK: servers.operation_id -> operations.id
    if pg:
        op.create_foreign_key(
            "fk_servers_operation_id",
            "servers",
            "operations",
            ["operation_id"],
            ["id"],
            ondelete="CASCADE",
        )
    else:
        with op.batch_alter_table("servers") as batch:
            batch.create_foreign_key(
                "fk_servers_operation_id",
                "operations",
                ["operation_id"],
                ["id"],
                ondelete="CASCADE",
            )

    op.create_table(
        "server_variables",
        sa.Column(
            "id",
            GUID(),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("server_id", GUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("default_value", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("enum", json_variant(), nullable=True),
        sa.Column("extensions", json_variant(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_server_variables_created_at", "server_variables", ["created_at"])
    op.create_index("ix_server_variables_created_by", "server_variables", ["created_by"])

    op.create_table(
        "operation_url_indexes",
        sa.Column(
            "id",
            GUID(),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("operation_id", sa.String(50), nullable=False),
        sa.Column("revision_id", GUID(), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("host", sa.Text, nullable=True),
        sa.Column("host_regex", sa.Text, nullable=True),
        sa.Column("path_template", sa.Text, nullable=False),
        sa.Column("path_regex", sa.Text, nullable=False),
        sa.Column("param_names", text_array_variant(), nullable=False),
        sa.Column("segment_count", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revision_id"], ["api_revisions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "method",
            "host",
            "host_regex",
            "path_template",
            name="uq_operation_url_index_lookup",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        "ix_operation_url_index_method_host_revision",
        "operation_url_indexes",
        ["method", "host", "revision_id", "path_template"],
    )
    op.create_index(
        "ix_operation_url_index_operation_id", "operation_url_indexes", ["operation_id"]
    )
    op.create_index("ix_operation_url_index_revision_id", "operation_url_indexes", ["revision_id"])
    op.create_index("ix_operation_url_indexes_created_at", "operation_url_indexes", ["created_at"])
    op.create_index("ix_operation_url_indexes_created_by", "operation_url_indexes", ["created_by"])

    op.create_table(
        "security_schemes",
        sa.Column(
            "id",
            GUID(),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("revision_id", GUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("scheme", sa.String(50), nullable=True),
        sa.Column("bearer_format", sa.String(50), nullable=True),
        sa.Column("in", sa.String(50), nullable=True),
        sa.Column("param_name", sa.String(100), nullable=True),
        sa.Column("open_id_connect_url", sa.Text, nullable=True),
        sa.Column("raw_scheme", json_variant(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["revision_id"], ["api_revisions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("revision_id", "name", name="uq_security_schemes_revision_name"),
    )
    op.create_index("ix_security_schemes_revision_id", "security_schemes", ["revision_id"])
    op.create_index("ix_security_schemes_created_at", "security_schemes", ["created_at"])
    op.create_index("ix_security_schemes_created_by", "security_schemes", ["created_by"])

    op.create_table(
        "security_scheme_flows",
        sa.Column(
            "id",
            GUID(),
            server_default=uuid_default,
            nullable=False,
        ),
        sa.Column("security_scheme_id", GUID(), nullable=False),
        sa.Column("flow_type", sa.String(50), nullable=False),
        sa.Column("authorization_url", sa.Text, nullable=True),
        sa.Column("token_url", sa.Text, nullable=True),
        sa.Column("refresh_url", sa.Text, nullable=True),
        sa.Column("scopes", json_variant(), nullable=True),
        sa.Column("raw_flow", json_variant(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["security_scheme_id"], ["security_schemes.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_security_scheme_flows_scheme_id", "security_scheme_flows", ["security_scheme_id"]
    )
    op.create_index("ix_security_scheme_flows_created_at", "security_scheme_flows", ["created_at"])
    op.create_index("ix_security_scheme_flows_created_by", "security_scheme_flows", ["created_by"])


def downgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"

    if pg:
        op.drop_constraint("fk_servers_operation_id", "servers", type_="foreignkey")
        op.drop_constraint("fk_apis_current_revision_id", "apis", type_="foreignkey")

    op.drop_table("security_scheme_flows")
    op.drop_table("security_schemes")
    op.drop_table("operation_url_indexes")
    op.drop_table("server_variables")
    op.drop_table("servers")
    op.drop_table("operations")
    op.drop_table("spec_files")
    op.drop_table("api_revisions")
    op.drop_table("apis")
    if pg:
        op.execute("DROP FUNCTION IF EXISTS generate_ksuid(text)")
