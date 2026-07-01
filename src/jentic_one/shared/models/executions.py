"""Execution-record enums shared across modules."""

from enum import StrEnum


class ExecutionStatus(StrEnum):
    """Terminal execution statuses exposed via the API."""

    COMPLETED = "completed"
    FAILED = "failed"
