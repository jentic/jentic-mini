"""Registry-related enums shared across modules."""

from enum import StrEnum


class ApiRevisionState(StrEnum):
    """Lifecycle state of an API revision."""

    DRAFT = "draft"
    PUBLISHED = "published"
    IMPORTED = "imported"
    ARCHIVED = "archived"


class ApiRevisionSourceType(StrEnum):
    """Source type for an API revision spec."""

    URL = "url"
    INLINE = "inline"
    UNKNOWN = "unknown"


class OverlayStatus(StrEnum):
    """Lifecycle status of an overlay."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    DEPRECATED = "deprecated"
