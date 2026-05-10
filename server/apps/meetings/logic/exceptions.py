class MeetingNotFoundError(Exception):
    """Raised when a meeting lookup by id returns no row."""


class GroupNotFoundError(Exception):
    """Raised when the parent group lookup fails."""


class PermissionDeniedError(Exception):
    """Raised when the requesting user lacks the required role or access."""


class MeetingDateConflictError(Exception):
    """Raised when (group, date) collides with an existing meeting."""
