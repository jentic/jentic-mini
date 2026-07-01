"""Unit tests for upstream URL validation."""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from jentic_one.shared.config import EgressConfig
from jentic_one.shared.url_validation import validate_upstream_url


def test_valid_https_url() -> None:
    assert validate_upstream_url("https://api.example.com/v1") == "https://api.example.com/v1"


def test_valid_http_url() -> None:
    assert validate_upstream_url("http://api.example.com/v1") == "http://api.example.com/v1"


def test_adds_https_scheme() -> None:
    assert validate_upstream_url("api.example.com/v1") == "https://api.example.com/v1"


def test_rejects_empty_string() -> None:
    with pytest.raises(ValueError, match="upstream URL is required"):
        validate_upstream_url("")


def test_rejects_whitespace_only() -> None:
    with pytest.raises(ValueError, match="upstream URL is required"):
        validate_upstream_url("   ")


def test_rejects_loopback_ip() -> None:
    with pytest.raises(ValueError, match="blocked address range"):
        validate_upstream_url("http://127.0.0.1/foo")


def test_rejects_private_10_network() -> None:
    with pytest.raises(ValueError, match="blocked address range"):
        validate_upstream_url("http://10.0.0.1/foo")


def test_rejects_private_172_network() -> None:
    with pytest.raises(ValueError, match="blocked address range"):
        validate_upstream_url("http://172.16.0.1/foo")


def test_rejects_private_192_network() -> None:
    with pytest.raises(ValueError, match="blocked address range"):
        validate_upstream_url("http://192.168.1.1/foo")


def test_rejects_link_local() -> None:
    with pytest.raises(ValueError, match="blocked address range"):
        validate_upstream_url("http://169.254.169.254/latest/meta-data/")


def test_rejects_metadata_hostname() -> None:
    with pytest.raises(ValueError, match="blocked hostname"):
        validate_upstream_url("http://metadata.google.internal/computeMetadata/v1/")


def test_rejects_ipv6_loopback() -> None:
    with pytest.raises(ValueError, match="blocked address range"):
        validate_upstream_url("http://[::1]/foo")


def test_rejects_no_hostname() -> None:
    with pytest.raises(ValueError, match="no hostname"):
        validate_upstream_url("http:///path")


def test_rejects_zero_network() -> None:
    with pytest.raises(ValueError, match="blocked address range"):
        validate_upstream_url("http://0.0.0.1/foo")


def test_hostname_resolving_to_private_ip_blocked() -> None:
    fake_result = [(2, 1, 6, "", ("169.254.169.254", 0))]
    with (
        patch("jentic_one.shared.url_validation.socket.getaddrinfo", return_value=fake_result),
        pytest.raises(ValueError, match="blocked address range"),
    ):
        validate_upstream_url("http://evil.attacker.com/metadata")


def test_hostname_resolving_to_public_ip_allowed() -> None:
    fake_result = [(2, 1, 6, "", ("93.184.216.34", 0))]
    with patch("jentic_one.shared.url_validation.socket.getaddrinfo", return_value=fake_result):
        result = validate_upstream_url("http://example.com/api")
        assert result == "http://example.com/api"


def test_dns_resolution_failure_allows_url() -> None:
    with patch(
        "jentic_one.shared.url_validation.socket.getaddrinfo",
        side_effect=socket.gaierror("Name resolution failed"),
    ):
        result = validate_upstream_url("http://nonexistent.example.com/api")
        assert result == "http://nonexistent.example.com/api"


# --- §08 E2: configurable internal-egress allowlist -------------------------


def test_default_egress_is_strict() -> None:
    # An empty (default) EgressConfig must behave exactly like no policy: strict.
    with pytest.raises(ValueError, match="blocked address range"):
        validate_upstream_url("http://10.50.2.10/api", EgressConfig())


def test_allowlisted_subnet_permits_ip_literal() -> None:
    egress = EgressConfig(allowed_private_subnets=["10.50.0.0/16"])
    assert validate_upstream_url("http://10.50.2.10/api", egress) == "http://10.50.2.10/api"


def test_private_ip_outside_allowlist_still_blocked() -> None:
    egress = EgressConfig(allowed_private_subnets=["10.50.0.0/16"])
    with pytest.raises(ValueError, match="blocked address range"):
        validate_upstream_url("http://10.60.0.1/api", egress)


def test_metadata_ip_blocked_even_when_range_allowlisted() -> None:
    # The covering /16 is allowlisted, but the IMDS IP is a hard, non-overridable deny.
    egress = EgressConfig(allowed_private_subnets=["169.254.0.0/16"])
    with pytest.raises(ValueError, match="blocked address range"):
        validate_upstream_url("http://169.254.169.254/latest/meta-data/", egress)


def test_ipv6_metadata_ip_blocked_even_when_range_allowlisted() -> None:
    egress = EgressConfig(allowed_private_subnets=["fc00::/7"])
    with pytest.raises(ValueError, match="blocked address range"):
        validate_upstream_url("http://[fd00:ec2::254]/latest/meta-data/", egress)


def test_internal_domain_resolving_into_allowed_subnet_permitted() -> None:
    egress = EgressConfig(
        allowed_private_subnets=["10.50.0.0/16"],
        allowed_internal_domains=[".svc.cluster.local"],
    )
    fake_result = [(2, 1, 6, "", ("10.50.2.10", 0))]
    with patch("jentic_one.shared.url_validation.socket.getaddrinfo", return_value=fake_result):
        result = validate_upstream_url("http://billing.svc.cluster.local/api", egress)
        assert result == "http://billing.svc.cluster.local/api"


def test_internal_domain_not_in_allowlist_blocked() -> None:
    # Resolves into the allowed subnet, but the host suffix isn't allowlisted.
    egress = EgressConfig(allowed_private_subnets=["10.50.0.0/16"])
    fake_result = [(2, 1, 6, "", ("10.50.2.10", 0))]
    with (
        patch("jentic_one.shared.url_validation.socket.getaddrinfo", return_value=fake_result),
        pytest.raises(ValueError, match="blocked address range"),
    ):
        validate_upstream_url("http://billing.svc.cluster.local/api", egress)


def test_allowed_domain_resolving_outside_allowed_subnet_blocked() -> None:
    # Host suffix is allowlisted, but it resolves to a private IP outside the
    # allowed subnet — still blocked (both checks must pass).
    egress = EgressConfig(
        allowed_private_subnets=["10.50.0.0/16"],
        allowed_internal_domains=[".svc.cluster.local"],
    )
    fake_result = [(2, 1, 6, "", ("192.168.1.5", 0))]
    with (
        patch("jentic_one.shared.url_validation.socket.getaddrinfo", return_value=fake_result),
        pytest.raises(ValueError, match="blocked address range"),
    ):
        validate_upstream_url("http://billing.svc.cluster.local/api", egress)


def test_domain_suffix_match_requires_dot_boundary() -> None:
    # "malinternal.corp" must NOT be matched by suffix "internal.corp".
    egress = EgressConfig(
        allowed_private_subnets=["10.50.0.0/16"],
        allowed_internal_domains=["internal.corp"],
    )
    fake_result = [(2, 1, 6, "", ("10.50.2.10", 0))]
    with (
        patch("jentic_one.shared.url_validation.socket.getaddrinfo", return_value=fake_result),
        pytest.raises(ValueError, match="blocked address range"),
    ):
        validate_upstream_url("http://malinternal.corp/api", egress)


def test_domain_exact_match_without_leading_dot() -> None:
    # Exact match on the bare domain works.
    egress = EgressConfig(
        allowed_private_subnets=["10.50.0.0/16"],
        allowed_internal_domains=["internal.corp"],
    )
    fake_result = [(2, 1, 6, "", ("10.50.2.10", 0))]
    with patch("jentic_one.shared.url_validation.socket.getaddrinfo", return_value=fake_result):
        result = validate_upstream_url("http://internal.corp/api", egress)
        assert result == "http://internal.corp/api"


def test_domain_subdomain_match_without_leading_dot() -> None:
    # "foo.internal.corp" should be matched by suffix "internal.corp".
    egress = EgressConfig(
        allowed_private_subnets=["10.50.0.0/16"],
        allowed_internal_domains=["internal.corp"],
    )
    fake_result = [(2, 1, 6, "", ("10.50.2.10", 0))]
    with patch("jentic_one.shared.url_validation.socket.getaddrinfo", return_value=fake_result):
        result = validate_upstream_url("http://foo.internal.corp/api", egress)
        assert result == "http://foo.internal.corp/api"


def test_invalid_cidr_in_config_rejected() -> None:
    with pytest.raises(ValueError, match="invalid CIDR"):
        EgressConfig(allowed_private_subnets=["not-a-cidr"])
