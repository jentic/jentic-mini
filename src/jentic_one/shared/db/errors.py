"""Domain-level database exceptions."""


class DatabaseIntegrityError(Exception):
    """Raised when a transaction fails due to an integrity constraint violation."""

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail)
        self.detail = detail


class DatabaseUnavailableError(Exception):
    """Raised when a transient database failure persists after retries."""

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail)
        self.detail = detail
