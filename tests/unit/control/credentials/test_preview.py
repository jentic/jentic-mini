"""Unit tests for preview derivation via EncryptionService.preview()."""

from __future__ import annotations

from jentic_one.shared.crypto.encryption import EncryptionService


def test_preview_normal_token() -> None:
    assert EncryptionService.preview("sk-1234567890abcdef") == "…def"


def test_preview_short_token_masked() -> None:
    assert EncryptionService.preview("ab") == "…***"


def test_preview_exactly_three_chars_masked() -> None:
    assert EncryptionService.preview("abc") == "…***"


def test_preview_four_chars_shows_last_three() -> None:
    assert EncryptionService.preview("abcd") == "…bcd"


def test_preview_empty_string_masked() -> None:
    assert EncryptionService.preview("") == "…***"
