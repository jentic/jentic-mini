"""Admin module service layer.

Services are imported directly from their modules to avoid circular imports:

    from jentic_one.admin.services.auth_service import AuthService
    from jentic_one.admin.services.user_service import UserService
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jentic_one.admin.services.audit_service import AuditService
    from jentic_one.admin.services.auth_service import AuthService
    from jentic_one.admin.services.event_service import EventService
    from jentic_one.admin.services.event_stream_service import EventStreamService
    from jentic_one.admin.services.execution_service import ExecutionService
    from jentic_one.admin.services.health_service import HealthService
    from jentic_one.admin.services.invite_service import InviteService
    from jentic_one.admin.services.job_result_service import JobResultService
    from jentic_one.admin.services.job_service import JobService
    from jentic_one.admin.services.monitoring_service import MonitoringService
    from jentic_one.admin.services.permission_service import PermissionService
    from jentic_one.admin.services.user_service import UserService

__all__ = [
    "AuditService",
    "AuthService",
    "EventService",
    "EventStreamService",
    "ExecutionService",
    "HealthService",
    "InviteService",
    "JobResultService",
    "JobService",
    "MonitoringService",
    "PermissionService",
    "UserService",
]


def __getattr__(name: str) -> type:
    """Lazy import to avoid circular dependency with repos."""
    _module_map = {
        "AuditService": "jentic_one.admin.services.audit_service",
        "AuthService": "jentic_one.admin.services.auth_service",
        "EventService": "jentic_one.admin.services.event_service",
        "EventStreamService": "jentic_one.admin.services.event_stream_service",
        "ExecutionService": "jentic_one.admin.services.execution_service",
        "HealthService": "jentic_one.admin.services.health_service",
        "InviteService": "jentic_one.admin.services.invite_service",
        "JobResultService": "jentic_one.admin.services.job_result_service",
        "JobService": "jentic_one.admin.services.job_service",
        "MonitoringService": "jentic_one.admin.services.monitoring_service",
        "PermissionService": "jentic_one.admin.services.permission_service",
        "UserService": "jentic_one.admin.services.user_service",
    }
    if name in _module_map:
        module = importlib.import_module(_module_map[name])
        return getattr(module, name)  # type: ignore[no-any-return]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
