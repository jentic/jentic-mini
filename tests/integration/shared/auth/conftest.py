from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from jentic_one.shared.context import Context


@pytest.fixture()
async def ctx(integration_context: Context) -> AsyncGenerator[Context, None]:
    """Short alias for integration_context used by auth verification tests."""
    yield integration_context
