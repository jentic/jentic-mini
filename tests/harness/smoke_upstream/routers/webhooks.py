"""Webhook-subscription router (OpenAPI 3.1 ``webhooks``).

``POST /webhooks/subscribe`` registers a ``callback_url`` and fires a best-effort
out-of-band POST back to it after a short delay. Scope note: like
``/callbacks``, this exercises the **platform/network**, not the broker — the
webhook fires upstream -> listener directly and does NOT traverse the broker.
Broker-mediated webhook ingress is a deferred capability, not under test here.
"""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

from tests.harness.smoke_upstream.routers._callbacks_util import schedule_post_back

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

WEBHOOK_EVENT: Final = "payment.succeeded"

STATE_WEBHOOK_TASK: Final = "webhook_task"


class WebhookSubscription(BaseModel):
    callback_url: str


@router.post("/subscribe")
async def webhooks_subscribe(body: WebhookSubscription, request: Request) -> JSONResponse:
    payload: dict[str, object] = {"event": WEBHOOK_EVENT}
    task = schedule_post_back(body.callback_url, payload)
    setattr(request.app.state, STATE_WEBHOOK_TASK, task)
    return JSONResponse(status_code=202, content={"status": "subscribed"})
