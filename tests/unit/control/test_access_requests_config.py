"""Unit tests for access_requests configuration defaults and env overrides."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from jentic_one.shared.config import load_config


def test_access_requests_defaults(config_file: Path) -> None:
    config = load_config(config_file)
    assert config.control.access_requests.ttl_days == 7
    assert config.control.access_requests.canonical_base_url == ""


def test_access_requests_ttl_days_env_override(config_file: Path) -> None:
    env = {"JENTIC__CONTROL__ACCESS_REQUESTS__TTL_DAYS": "14"}
    with patch.dict(os.environ, env, clear=False):
        config = load_config(config_file)
    assert config.control.access_requests.ttl_days == 14


def test_access_requests_canonical_base_url_env_override(config_file: Path) -> None:
    env = {"JENTIC__CONTROL__ACCESS_REQUESTS__CANONICAL_BASE_URL": "https://app.example.com"}
    with patch.dict(os.environ, env, clear=False):
        config = load_config(config_file)
    assert config.control.access_requests.canonical_base_url == "https://app.example.com"
