"""OpenAPI schema helpers and extensions for Jentic Mini.

Provides reusable utilities for enhancing OpenAPI documentation with
agent-specific metadata (x-agent-hints) and other custom extensions.
"""


def agent_hints(
    when_to_use: str,
    prerequisites: list[str] | None = None,
    avoid_when: str | None = None,
    related_operations: list[str] | None = None,
) -> dict:
    """Build x-agent-hints extension for an operation.

    x-agent-hints provides guidance to AI agents about when and how to use
    an operation. This metadata helps agents make better decisions about
    which operations to call and in what order.

    Args:
        when_to_use: Clear description of when this operation should be used.
        prerequisites: List of requirements before calling (credentials, prior steps, etc.)
        avoid_when: Situations where this operation should NOT be used.
        related_operations: Other operations commonly used before/after this one.

    Returns:
        Dict suitable for FastAPI's openapi_extra parameter.

    Example:
        @router.get(
            "/search",
            summary="Search the catalog",
            openapi_extra=agent_hints(
                when_to_use="Use when discovering APIs by natural language intent",
                prerequisites=["Requires authentication"],
                avoid_when="Do not use if you already know the operation ID",
                related_operations=["GET /inspect/{id}", "GET /apis"]
            ),
        )
    """
    hints = {"when_to_use": when_to_use}

    if prerequisites:
        hints["prerequisites"] = prerequisites
    if avoid_when:
        hints["avoid_when"] = avoid_when
    if related_operations:
        hints["related_operations"] = related_operations

    return {"x-agent-hints": hints}
