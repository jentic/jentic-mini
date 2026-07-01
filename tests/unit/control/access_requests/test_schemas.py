"""Unit tests for access-request web schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from jentic_one.control.web.schemas.access_requests import (
    AccessRequestFileRequest,
    AccessRequestItemRequest,
    AmendItemSchema,
    AmendRequest,
    DecideItemSchema,
    DecideRequest,
    PermissionRuleSchema,
)


def test_permission_rule_valid_allow_effect() -> None:
    rule = PermissionRuleSchema(effect="allow", methods=["GET"])
    assert rule.effect == "allow"


def test_permission_rule_valid_deny_effect() -> None:
    rule = PermissionRuleSchema(effect="deny", path="/secrets")
    assert rule.effect == "deny"


def test_permission_rule_valid_require_approval_effect() -> None:
    rule = PermissionRuleSchema(effect="require-approval")
    assert rule.effect == "require-approval"


def test_permission_rule_condition_less_allow_rejected() -> None:
    with pytest.raises(ValidationError, match="must constrain at least one"):
        PermissionRuleSchema(effect="allow")


def test_permission_rule_condition_less_deny_accepted() -> None:
    # A catch-all deny is a legitimate default-deny construct.
    rule = PermissionRuleSchema(effect="deny")
    assert rule.effect == "deny"


def test_permission_rule_condition_less_require_approval_accepted() -> None:
    rule = PermissionRuleSchema(effect="require-approval")
    assert rule.effect == "require-approval"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"methods": ["GET"]},
        {"path": "/v1/users"},
        {"operations": ["getUser"]},
    ],
)
def test_permission_rule_constrained_allow_accepted(kwargs: dict[str, object]) -> None:
    rule = PermissionRuleSchema(effect="allow", **kwargs)  # type: ignore[arg-type]
    assert rule.effect == "allow"


def test_permission_rule_invalid_effect_rejected() -> None:
    with pytest.raises(ValidationError, match="effect"):
        PermissionRuleSchema(effect="invalid")  # type: ignore[arg-type]


def test_permission_rule_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError, match="extra"):
        PermissionRuleSchema(effect="allow", unknown_field="bad")  # type: ignore[call-arg]


def test_item_request_accepts_resource_id_only() -> None:
    item = AccessRequestItemRequest(
        resource_type="credential", action="bind", resource_id="cred_123"
    )
    assert item.resource_id == "cred_123"
    assert item.resource_reference is None


def test_item_request_accepts_resource_reference_only() -> None:
    item = AccessRequestItemRequest(
        resource_type="toolkit", action="bind", resource_reference={"vendor": "acme"}
    )
    assert item.resource_reference == {"vendor": "acme"}
    assert item.resource_id is None


def test_item_request_accepts_neither_resource_target() -> None:
    item = AccessRequestItemRequest(resource_type="toolkit", action="bind")
    assert item.resource_id is None
    assert item.resource_reference is None


def test_item_request_rejects_both_resource_targets() -> None:
    with pytest.raises(ValidationError, match=r"resource_id.*resource_reference"):
        AccessRequestItemRequest(
            resource_type="credential",
            action="bind",
            resource_id="cred_123",
            resource_reference={"vendor": "x"},
        )


def test_item_request_rejects_unknown_resource_type() -> None:
    with pytest.raises(ValidationError, match="resource_type"):
        AccessRequestItemRequest(resource_type="api", action="bind")  # type: ignore[arg-type]


def test_item_request_rejects_unsupported_combination() -> None:
    with pytest.raises(ValidationError, match="Unsupported resource_type/action"):
        AccessRequestItemRequest(resource_type="scope", action="bind")


def test_file_request_valid_with_items() -> None:
    req = AccessRequestFileRequest(
        reason="Need access",
        items=[AccessRequestItemRequest(resource_type="toolkit", action="bind")],
    )
    assert len(req.items) == 1


def test_file_request_empty_items_rejected() -> None:
    with pytest.raises(ValidationError, match="items"):
        AccessRequestFileRequest(reason="Need access", items=[])


def test_decide_item_valid_approved() -> None:
    item = DecideItemSchema(item_id="arqi_123", decision="approved")
    assert item.decision == "approved"


def test_decide_item_valid_denied() -> None:
    item = DecideItemSchema(item_id="arqi_123", decision="denied")
    assert item.decision == "denied"


def test_decide_item_invalid_decision_rejected() -> None:
    with pytest.raises(ValidationError, match="decision"):
        DecideItemSchema(item_id="arqi_123", decision="maybe")  # type: ignore[arg-type]


def test_decide_request_valid() -> None:
    req = DecideRequest(items=[DecideItemSchema(item_id="arqi_1", decision="approved")])
    assert len(req.items) == 1


def test_decide_request_empty_items_rejected() -> None:
    with pytest.raises(ValidationError, match="items"):
        DecideRequest(items=[])


def test_amend_request_valid() -> None:
    req = AmendRequest(
        items=[
            AmendItemSchema(
                item_id="arqi_1", rules=[PermissionRuleSchema(effect="allow", methods=["GET"])]
            )
        ]
    )
    assert len(req.items) == 1


def test_amend_request_empty_items_rejected() -> None:
    with pytest.raises(ValidationError, match="items"):
        AmendRequest(items=[])
