"""Type-checking utility for pipeline context values."""

from typing import get_args, get_origin


def check_type(value: object, expected_type: type) -> bool:
    """Check if a value matches an expected type, including generics."""
    origin = get_origin(expected_type)
    args = get_args(expected_type)

    if origin is None:
        return isinstance(value, expected_type)

    if origin in (list, set, tuple):
        if not isinstance(value, origin):
            return False
        if args:
            return all(isinstance(item, args[0]) for item in value)
        return True

    if origin is dict:
        if not isinstance(value, dict):
            return False
        if args:
            key_type, val_type = args
            return all(
                isinstance(k, key_type) and isinstance(v, val_type) for k, v in value.items()
            )
        return True

    return isinstance(value, origin)
