"""Shared service-error to Problem Details handler factory.

Surfaces supply their error map and an optional response hook; the factory
returns a handler function that implements the standard MRO-walk, logging,
and Problem Details response construction.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine, Mapping
from typing import Any

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from jentic.problem_details import ProblemDetailException

ResponseHook = Callable[[Request, Exception, int, JSONResponse], JSONResponse]
ServiceErrorHandler = Callable[[Request, Any], Coroutine[Any, Any, JSONResponse]]


def make_service_error_handler(
    error_map: Mapping[type[Exception], tuple[int, str]],
    *,
    response_hook: ResponseHook | None = None,
    safe_details: Mapping[type[Exception], str] | None = None,
) -> ServiceErrorHandler:
    """Create a service-error handler that maps exceptions to Problem Details responses.

    Args:
        error_map: Mapping from exception classes to (status_code, type_slug) tuples.
        response_hook: Optional callback to mutate the response before returning
            (e.g. adding custom headers). Signature:
            ``(request, exc, status_code, response) -> response``.
        safe_details: Optional mapping from exception class to a static, generic
            ``detail`` string to send to the client *instead* of ``str(exc)``. Use
            this for infrastructure errors whose raw message would leak internals
            (e.g. a wrapped SQLAlchemy ``OperationalError`` carrying the full SQL
            statement, bound parameters, and connection URL — CWE-209). The raw
            ``str(exc)`` is still logged server-side for diagnosis.
    """
    logger = structlog.get_logger("jentic_one.shared.web.errors")

    async def handler(request: Request, exc: Exception) -> JSONResponse:
        for error_cls in type(exc).__mro__:
            if error_cls in error_map:
                status_code, type_slug = error_map[error_cls]
                safe_detail = safe_details.get(error_cls) if safe_details else None
                problem = ProblemDetailException(
                    status_code=status_code,
                    detail=safe_detail if safe_detail is not None else str(exc),
                    type=type_slug,
                    instance=request.url.path,
                )
                if status_code >= 500:
                    logger.error(
                        "unhandled_service_error",
                        status=status_code,
                        type=type_slug,
                        path=request.url.path,
                        exc_info=exc,
                    )
                else:
                    logger.warning(
                        "client_error",
                        status=status_code,
                        type=type_slug,
                        path=request.url.path,
                        # When the client detail is sanitised, keep the raw message
                        # server-side so the conflict is still diagnosable.
                        **({"raw_detail": str(exc)} if safe_detail is not None else {}),
                    )
                response = JSONResponse(
                    status_code=problem.status_code,
                    content=problem.detail,
                    media_type="application/problem+json",
                )
                if response_hook is not None:
                    response = response_hook(request, exc, status_code, response)
                return response

        logger.error("unknown_service_error", path=request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"type": "server_error", "detail": "An unexpected error occurred"},
            media_type="application/problem+json",
        )

    return handler
