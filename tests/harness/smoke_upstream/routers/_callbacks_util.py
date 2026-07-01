"""Shared best-effort callback post-back helper for the callbacks/webhooks routers.

Both routers fire an out-of-band HTTP POST back to a caller-supplied URL after a
short delay. This is a **platform/network** concern: the post-back goes
upstream -> listener directly and never traverses the broker (the broker is an
egress-only proxy with no inbound webhook-routing surface). The post is
best-effort — connection errors are swallowed.

Tests inject a captured-calls client via :func:`set_callback_client` (typically
an ``httpx.AsyncClient`` wrapping an in-process ASGI listener) so no real
network is needed, and schedule the post-back as an awaitable task they can
await deterministically rather than sleeping.
"""

from __future__ import annotations

import asyncio
from typing import Final

import httpx

CALLBACK_DELAY_SECONDS: Final = 0.1

_callback_client: httpx.AsyncClient | None = None


def set_callback_client(client: httpx.AsyncClient | None) -> None:
    """Override the client used for post-backs (tests inject an ASGI client)."""
    global _callback_client
    _callback_client = client


def _resolve_client() -> tuple[httpx.AsyncClient, bool]:
    if _callback_client is not None:
        return _callback_client, False
    return httpx.AsyncClient(), True


async def post_back(callback_url: str, payload: dict[str, object]) -> None:
    """Best-effort delayed POST to *callback_url*; swallows transport errors."""
    await asyncio.sleep(CALLBACK_DELAY_SECONDS)
    client, owned = _resolve_client()
    try:
        await client.post(callback_url, json=payload)
    except httpx.HTTPError:
        return
    finally:
        if owned:
            await client.aclose()


def schedule_post_back(callback_url: str, payload: dict[str, object]) -> asyncio.Task[None]:
    """Schedule :func:`post_back` and return the task for deterministic awaiting."""
    return asyncio.create_task(post_back(callback_url, payload))
