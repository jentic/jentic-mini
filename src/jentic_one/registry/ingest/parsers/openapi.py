"""OpenAPI operation parser — extracts operation metadata from spec documents."""

from typing import Any

import structlog

from jentic_one.registry.ingest.observability import spec_path_count, tracer

logger = structlog.get_logger()

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


class OpenAPIOperationParser:
    """Parses an OpenAPI spec and extracts operation definitions."""

    def extract_operations(self, spec: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract all operations from an OpenAPI specification."""
        paths: dict[str, Any] = spec.get("paths", {})
        if not paths:
            logger.debug("no_paths_in_spec")
            return []

        with tracer.start_as_current_span("ingest.parse_openapi"):
            spec_path_count.record(len(paths))
            logger.debug("paths_found", count=len(paths))
            operations: list[dict[str, Any]] = []

            for path, path_item in paths.items():
                if not isinstance(path_item, dict):
                    continue

                path_servers: list[dict[str, Any]] = path_item.get("servers", [])

                for method, operation in path_item.items():
                    if method not in HTTP_METHODS:
                        continue
                    if not isinstance(operation, dict):
                        continue

                    op = self._process_operation(path, method, operation, path_servers)
                    operations.append(op)

        logger.debug("operations_extracted", count=len(operations))
        return operations

    def _process_operation(
        self,
        path: str,
        method: str,
        operation: dict[str, Any],
        path_servers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Process a single operation into the canonical output shape."""
        operation_servers: list[dict[str, Any]] = operation.get("servers", [])
        servers = operation_servers if operation_servers else path_servers

        return {
            "operation_id": operation.get("operationId"),
            "path": path,
            "method": method.upper(),
            "summary": operation.get("summary"),
            "description": operation.get("description"),
            "tags": operation.get("tags", []),
            "servers": servers,
        }
