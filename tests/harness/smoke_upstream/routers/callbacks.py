"""Callback-trigger router (OpenAPI ``callbacks``).

``POST /callbacks/trigger`` accepts a ``callback_url`` and fires a best-effort
out-of-band POST back to it after a short delay. Scope note: this exercises the
**platform/network**, not the broker — the callback fires upstream -> listener
directly and does NOT flow back through the broker (egress-only, no inbound
webhook surface). Broker-mediated webhook ingress is a deferred capability.
"""

from __future__ import annotations

import uuid
from typing import Final

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

from tests.harness.smoke_upstream.routers._callbacks_util import schedule_post_back

router = APIRouter(prefix="/callbacks", tags=["callbacks"])

CALLBACK_EVENT: Final = "callback.fired"

STATE_CALLBACK_TASK: Final = "callback_task"


class CallbackTrigger(BaseModel):
    callback_url: str


@router.post("/trigger")
async def callbacks_trigger(body: CallbackTrigger, request: Request) -> JSONResponse:
    payload: dict[str, object] = {"event": CALLBACK_EVENT, "id": str(uuid.uuid4())}
    task = schedule_post_back(body.callback_url, payload)
    setattr(request.app.state, STATE_CALLBACK_TASK, task)
    return JSONResponse(status_code=202, content={"status": "accepted"})
