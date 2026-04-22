"""Policy engine tests — the core enforcement logic.

Tests _check_policy directly (pure function) and verifies the
system safety rules behave as documented.
"""

from src.routers.toolkits import _check_policy


class TestSystemSafetyRulesAlone:
    """No agent rules — just system safety defaults."""

    def test_denies_post(self):
        allowed, _ = _check_policy([], None, method="POST", path="/v1/pages")
        assert not allowed

    def test_denies_put(self):
        allowed, _ = _check_policy([], None, method="PUT", path="/v1/pages/123")
        assert not allowed

    def test_denies_patch(self):
        allowed, _ = _check_policy([], None, method="PATCH", path="/v1/pages/123")
        assert not allowed

    def test_denies_delete(self):
        allowed, _ = _check_policy([], None, method="DELETE", path="/v1/pages/123")
        assert not allowed

    def test_allows_get(self):
        allowed, _ = _check_policy([], None, method="GET", path="/v1/pages")
        assert allowed

    def test_denies_sensitive_paths_even_for_get(self):
        for path in [
            "/admin/users",
            "/billing/invoices",
            "/webhook/config",
            "/secret/keys",
            "/token/refresh",
        ]:
            allowed, _ = _check_policy([], None, method="GET", path=path)
            assert not allowed, f"GET {path} should be denied by sensitive path rule"


class TestAgentRulesOverride:
    """Agent rules placed before system rules can grant write access."""

    def test_allow_rule_grants_write(self):
        rules = [{"effect": "allow", "methods": ["POST"], "path": "pages"}]
        allowed, _ = _check_policy(rules, None, method="POST", path="/v1/pages")
        assert allowed

    def test_allow_rule_does_not_match_other_paths(self):
        rules = [{"effect": "allow", "methods": ["POST"], "path": "pages"}]
        allowed, _ = _check_policy(rules, None, method="POST", path="/v1/users")
        assert not allowed  # falls through to system deny

    def test_allow_rule_does_not_match_other_methods(self):
        rules = [{"effect": "allow", "methods": ["POST"], "path": "pages"}]
        allowed, _ = _check_policy(rules, None, method="DELETE", path="/v1/pages/123")
        assert not allowed  # DELETE not in allowed methods


class TestFirstMatchWins:
    """Rule evaluation is first-match-wins."""

    def test_deny_before_allow(self):
        rules = [
            {"effect": "deny", "methods": ["POST"], "path": "pages"},
            {"effect": "allow", "methods": ["POST"], "path": "pages"},
        ]
        allowed, _ = _check_policy(rules, None, method="POST", path="/v1/pages")
        assert not allowed

    def test_allow_before_deny(self):
        rules = [
            {"effect": "allow", "methods": ["POST"], "path": "pages"},
            {"effect": "deny", "methods": ["POST"], "path": "pages"},
        ]
        allowed, _ = _check_policy(rules, None, method="POST", path="/v1/pages")
        assert allowed


class TestPathRegexMatching:
    """Path matching uses re.search (substring match)."""

    def test_substring_match(self):
        rules = [{"effect": "allow", "methods": ["POST"], "path": "drafts"}]
        allowed, _ = _check_policy(rules, None, method="POST", path="/gmail/v1/users/me/drafts")
        assert allowed

    def test_no_match_on_unrelated_path(self):
        rules = [{"effect": "allow", "methods": ["POST"], "path": "drafts"}]
        allowed, _ = _check_policy(
            rules, None, method="POST", path="/gmail/v1/users/me/messages/send"
        )
        assert not allowed
