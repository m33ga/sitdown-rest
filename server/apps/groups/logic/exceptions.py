class GroupNotFoundError(Exception):
    """Raised when a group lookup by id returns no row."""


class PermissionDeniedError(Exception):
    """Raised when the requesting user lacks the required role or access."""
