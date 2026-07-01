"""Unit tests for the type-check utility."""

from jentic_one.registry.ingest._typecheck import check_type


def test_int_matches() -> None:
    assert check_type(42, int) is True


def test_str_matches() -> None:
    assert check_type("hello", str) is True


def test_int_rejects_str() -> None:
    assert check_type("hello", int) is False


def test_none_matches_nonetype() -> None:
    assert check_type(None, type(None)) is True


def test_list_int_accepts() -> None:
    assert check_type([1, 2, 3], list[int]) is True


def test_list_int_rejects_str_elements() -> None:
    assert check_type(["a", "b"], list[int]) is False


def test_empty_list_accepts() -> None:
    assert check_type([], list[int]) is True


def test_non_list_rejects() -> None:
    assert check_type((1, 2), list[int]) is False


def test_set_str_accepts() -> None:
    assert check_type({"a", "b"}, set[str]) is True


def test_set_str_rejects_int_elements() -> None:
    assert check_type({1, 2}, set[str]) is False


def test_dict_str_int_accepts() -> None:
    assert check_type({"a": 1, "b": 2}, dict[str, int]) is True


def test_dict_str_int_rejects_wrong_value_type() -> None:
    assert check_type({"a": "x"}, dict[str, int]) is False


def test_dict_str_int_rejects_wrong_key_type() -> None:
    assert check_type({1: 1}, dict[str, int]) is False


def test_non_dict_rejects() -> None:
    assert check_type([1, 2], dict[str, int]) is False


def test_tuple_accepts() -> None:
    assert check_type((1, 2, 3), tuple[int]) is True


def test_tuple_rejects_non_tuple() -> None:
    assert check_type([1, 2], tuple[int]) is False
