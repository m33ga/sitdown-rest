class GroupNotFoundError(Exception):
    """Raised when a group lookup by id returns no row."""


class PermissionDeniedError(Exception):
    """Raised when the requesting user lacks the required role or access."""


class MemberAlreadyExistsError(Exception):
    """Raised when attempting to add a user who is already a project member."""


class UserNotFoundError(Exception):
    """Raised when an add request targets a user_id that doesn't exist."""


class MemberNotFoundError(Exception):
    """Raised when removing a user who isn't a member of the group."""
