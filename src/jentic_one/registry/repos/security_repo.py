"""Repository for SecurityScheme entities."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from jentic_one.registry.core.schema.security_schemes import SecurityScheme, SecuritySchemeFlow


class SecurityRepository:
    """Data access layer for SecurityScheme entities — flush-only, never commits."""

    @staticmethod
    async def delete_for_revision(session: AsyncSession, revision_id: uuid.UUID) -> None:
        await session.execute(
            delete(SecurityScheme).where(SecurityScheme.revision_id == revision_id)
        )
        await session.flush()

    @staticmethod
    async def store_security_schemes(
        session: AsyncSession,
        *,
        revision_id: uuid.UUID,
        schemes: dict[str, dict[str, Any]],
        created_by: str,
    ) -> list[uuid.UUID]:
        scheme_objs: list[SecurityScheme] = []
        for name, scheme_data in schemes.items():
            scheme = SecurityScheme(
                revision_id=revision_id,
                name=name,
                type=scheme_data["type"],
                scheme=scheme_data.get("scheme"),
                bearer_format=scheme_data.get("bearerFormat"),
                in_location=scheme_data.get("in"),
                param_name=scheme_data.get("name"),
                open_id_connect_url=scheme_data.get("openIdConnectUrl"),
                description=scheme_data.get("description"),
                raw_scheme=scheme_data,
                created_by=created_by,
            )
            if scheme_data["type"] == "oauth2":
                flows: dict[str, Any] = scheme_data.get("flows", {})
                for flow_type, flow_data in flows.items():
                    flow = SecuritySchemeFlow(
                        flow_type=flow_type,
                        authorization_url=flow_data.get("authorizationUrl"),
                        token_url=flow_data.get("tokenUrl"),
                        refresh_url=flow_data.get("refreshUrl"),
                        scopes=flow_data.get("scopes"),
                        raw_flow=flow_data,
                        created_by=created_by,
                    )
                    scheme.flows.append(flow)
            scheme_objs.append(scheme)

        if not scheme_objs:
            return []

        session.add_all(scheme_objs)
        await session.flush()
        return [scheme.id for scheme in scheme_objs]

    @staticmethod
    async def get_by_revision(
        session: AsyncSession, revision_id: uuid.UUID
    ) -> list[SecurityScheme]:
        """Load all security schemes for a given revision."""
        stmt = select(SecurityScheme).where(SecurityScheme.revision_id == revision_id)
        result = await session.execute(stmt)
        return list(result.unique().scalars().all())
