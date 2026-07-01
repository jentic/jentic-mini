"""Unit tests for the OpenAPI operation parser."""

from typing import Any

from jentic_one.registry.ingest.parsers.openapi import OpenAPIOperationParser


def test_extracts_operations_from_minimal_spec() -> None:
    parser = OpenAPIOperationParser()
    spec: dict[str, Any] = {
        "openapi": "3.1.0",
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "listPets",
                    "summary": "List all pets",
                    "tags": ["pets"],
                },
                "post": {
                    "operationId": "createPet",
                    "summary": "Create a pet",
                    "tags": ["pets"],
                },
            },
            "/pets/{petId}": {
                "get": {
                    "operationId": "getPet",
                    "summary": "Get a pet",
                    "description": "Get a single pet by ID",
                    "tags": ["pets"],
                },
            },
        },
    }
    ops = parser.extract_operations(spec)
    assert len(ops) == 3
    op_ids = {op["operation_id"] for op in ops}
    assert op_ids == {"listPets", "createPet", "getPet"}


def test_non_http_keys_in_path_items_are_skipped() -> None:
    parser = OpenAPIOperationParser()
    spec: dict[str, Any] = {
        "paths": {
            "/items": {
                "parameters": [{"name": "limit", "in": "query"}],
                "summary": "Items endpoint",
                "get": {
                    "operationId": "listItems",
                },
            },
        },
    }
    ops = parser.extract_operations(spec)
    assert len(ops) == 1
    assert ops[0]["operation_id"] == "listItems"


def test_operation_servers_override_path_servers() -> None:
    parser = OpenAPIOperationParser()
    spec: dict[str, Any] = {
        "paths": {
            "/data": {
                "servers": [{"url": "https://path-level.example.com"}],
                "get": {
                    "operationId": "getData",
                    "servers": [{"url": "https://op-level.example.com"}],
                },
            },
        },
    }
    ops = parser.extract_operations(spec)
    assert len(ops) == 1
    assert ops[0]["servers"] == [{"url": "https://op-level.example.com"}]


def test_path_servers_used_when_no_operation_servers() -> None:
    parser = OpenAPIOperationParser()
    spec: dict[str, Any] = {
        "paths": {
            "/data": {
                "servers": [{"url": "https://path-level.example.com"}],
                "get": {
                    "operationId": "getData",
                },
            },
        },
    }
    ops = parser.extract_operations(spec)
    assert ops[0]["servers"] == [{"url": "https://path-level.example.com"}]


def test_missing_operation_id_yields_none() -> None:
    parser = OpenAPIOperationParser()
    spec: dict[str, Any] = {
        "paths": {
            "/things": {
                "get": {
                    "summary": "Get things",
                },
            },
        },
    }
    ops = parser.extract_operations(spec)
    assert len(ops) == 1
    assert ops[0]["operation_id"] is None


def test_empty_paths_returns_empty_list() -> None:
    parser = OpenAPIOperationParser()
    spec: dict[str, Any] = {"paths": {}}
    ops = parser.extract_operations(spec)
    assert ops == []


def test_no_paths_key_returns_empty_list() -> None:
    parser = OpenAPIOperationParser()
    spec: dict[str, Any] = {"openapi": "3.1.0"}
    ops = parser.extract_operations(spec)
    assert ops == []


def test_method_is_uppercased() -> None:
    parser = OpenAPIOperationParser()
    spec: dict[str, Any] = {
        "paths": {
            "/items": {
                "post": {"operationId": "create"},
            },
        },
    }
    ops = parser.extract_operations(spec)
    assert ops[0]["method"] == "POST"


def test_empty_servers_when_none_defined() -> None:
    parser = OpenAPIOperationParser()
    spec: dict[str, Any] = {
        "paths": {
            "/items": {
                "get": {"operationId": "list"},
            },
        },
    }
    ops = parser.extract_operations(spec)
    assert ops[0]["servers"] == []
