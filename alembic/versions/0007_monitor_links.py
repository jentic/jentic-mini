"""Monitor link columns + indexes.

Originally added jobs.agent_id (revision 0007). Extended in the same migration
to add cross-table linkage columns used by the Monitor page:

- jobs.agent_id          - tenant scoping for async jobs (mirrors executions.agent_id)
- executions.job_id      - reverse pointer: which async job (if any) produced this trace
- executions.parent_trace_id - parent workflow trace for child broker hops

Plus partial indexes for the lookups the Monitor surfaces depend on:
- idx_jobs_agent_created  - "list this agent's jobs over time"
- idx_executions_job_id   - "show all traces for this job"
- idx_executions_parent_trace - "show all child hops of this workflow trace"
- idx_jobs_trace_id       - "find the job that produced this trace" (cross-link badge)

All ALTERs are idempotent (PRAGMA-guarded). All indexes are partial (WHERE col
IS NOT NULL) so pre-feature rows don't pay storage cost.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-29
"""

from alembic import op
from sqlalchemy import text


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # ── jobs.agent_id ──────────────────────────────────────────────────────
    job_cols = {row[1] for row in bind.execute(text("PRAGMA table_info(jobs)"))}
    if "agent_id" not in job_cols:
        op.execute("ALTER TABLE jobs ADD COLUMN agent_id TEXT DEFAULT NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_agent_created "
        "ON jobs(agent_id, created_at) "
        "WHERE agent_id IS NOT NULL"
    )

    # ── executions.job_id, executions.parent_trace_id ──────────────────────
    exec_cols = {row[1] for row in bind.execute(text("PRAGMA table_info(executions)"))}
    if "job_id" not in exec_cols:
        op.execute("ALTER TABLE executions ADD COLUMN job_id TEXT DEFAULT NULL")
    if "parent_trace_id" not in exec_cols:
        op.execute("ALTER TABLE executions ADD COLUMN parent_trace_id TEXT DEFAULT NULL")

    # Cross-link lookups: small partial indexes keyed off the new columns.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_executions_job_id "
        "ON executions(job_id) "
        "WHERE job_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_executions_parent_trace "
        "ON executions(parent_trace_id) "
        "WHERE parent_trace_id IS NOT NULL"
    )
    # Reverse: "find the job for this trace". Used by the Execution Log
    # cross-link badge — needs to be cheap on every row render.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_trace_id "
        "ON jobs(trace_id) "
        "WHERE trace_id IS NOT NULL"
    )


def downgrade() -> None:
    # SQLite cannot DROP COLUMN cleanly — leave the new columns in place on
    # downgrade, same convention as 0005's executions.agent_id. Drop only
    # the indexes so the schema is structurally reversible.
    op.execute("DROP INDEX IF EXISTS idx_jobs_trace_id")
    op.execute("DROP INDEX IF EXISTS idx_executions_parent_trace")
    op.execute("DROP INDEX IF EXISTS idx_executions_job_id")
    op.execute("DROP INDEX IF EXISTS idx_jobs_agent_created")
