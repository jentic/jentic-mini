"""Weighted simple projection strategy (incumbent repetition-based approach)."""

from __future__ import annotations

from jentic_one.registry.core.schema.operations import Operation


class WeightedSimpleProjection:
    """
    Repetition-based projection strategy (incumbent approach).

    Creates text by repeating terms with different weights and using
    markers like "OPERATION_ID:", "API:", etc.
    """

    def create_projection(self, operation: Operation, vendor_id: str, api_name: str) -> str:
        """Create text projection using repetition/weighting approach."""
        # Use api_name if available, otherwise vendor_id
        api_identifier = api_name if api_name else vendor_id

        parts: list[str] = []

        # Create hierarchy: Workflows > Operations > APIs (inverted)

        # Add API name with lower weight (2x) - less important in the inverted hierarchy
        parts.extend([f"API: {api_identifier}"] * 2)

        # Add a clear separator for operation context
        parts.append("OPERATION_CONTEXT:")

        # Get method and path
        method = operation.method.upper()
        path = operation.path
        operation_id = operation.operation_id

        # If we have an operation_id, give it higher priority
        if operation_id:
            # Increase operation_id weight from 4x to 8x - make this the primary identifier
            parts.extend([f"OPERATION_ID: {operation_id}"] * 8)

            # Add the operation_id with spaces (more natural for search) with higher weight (3x)
            parts.extend([operation_id.replace("_", " ")] * 3)

            # Add method and path with medium weight (4x instead of 5x)
            parts.extend([f"OPERATION: {method} {path}"] * 4)
        else:
            # If no operation_id, increase the weight of method and path to 7x
            parts.extend([f"OPERATION: {method} {path}"] * 7)

            # Extract meaningful parts from the path for better searching
            path_parts = [p for p in path.split("/") if p and not p.startswith("{")]
            for part in path_parts:
                # Add each meaningful path segment with weight 2x
                parts.extend([part] * 2)

        # Add operation with API prefix for context
        parts.extend([f"{api_identifier} operation {method} {path}"] * 2)

        # Add summary with higher weight, especially if no operation_id
        summary = operation.summary or ""
        if summary:
            if operation_id:
                # With operation_id: moderate summary weight (3x)
                parts.extend([summary] * 3)
            else:
                # Without operation_id: high summary weight (5x)
                parts.extend([summary] * 5)

        # Add description with moderate weight
        description = operation.description or ""
        if description:
            if len(description) > 200:
                # Truncate overly long descriptions
                description = description[:200] + "..."

            # Add description with slightly higher weight (2x)
            parts.extend([description] * 2)

        # Add tags if available
        tags = operation.tags or []
        if tags:
            tags_text = f"Tags: {', '.join(tags)}"
            parts.append(tags_text)

        # Add API name at the end to bookend the text
        parts.append(f"API: {api_identifier}")

        # Join all parts with spaces
        return " ".join(parts)
