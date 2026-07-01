"""Health check service."""

from __future__ import annotations

from jentic_one.admin.repos import UserRepository
from jentic_one.admin.services.schemas.health import HealthView
from jentic_one.shared.context import Context


class HealthService:
    """Checks admin surface health and setup status."""

    def __init__(self, ctx: Context) -> None:
        self._ctx = ctx

    async def get_health(self) -> HealthView:
        async with self._ctx.admin_db.session() as session:
            user_count = await UserRepository.count(session)

        if user_count == 0:
            return HealthView(
                setup_required=True,
                next_step="create_admin",
            )
        return HealthView()
