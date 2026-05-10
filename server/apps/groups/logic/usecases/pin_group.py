"""Use case for ``PUT /groups/{id}/pin``."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import attrs
import structlog

from server.apps.groups.logic.exceptions import (
    GroupNotFoundError,
    PermissionDeniedError,
)

if TYPE_CHECKING:
    from server.apps.groups.infra.repository import GroupRepository
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class PinGroupUseCase:
    """Pin a group for the requesting user. Idempotent."""

    _group_repo: GroupRepository

    def __call__(self, user: User, group_id: UUID) -> None:
        """Run the use case; raises if the group is missing or no access."""
        log.debug(
            'pin_group_called',
            user_id=str(user.id),
            group_id=str(group_id),
        )
        group = self._group_repo.get_by_id(group_id)
        if group is None:
            log.debug(
                'pin_group_not_found',
                group_id=str(group_id),
            )
            raise GroupNotFoundError
        if (
            user.role != 'MANAGER'
            and not self._group_repo.is_member(user, group)
        ):
            log.debug(
                'pin_group_access_denied',
                user_id=str(user.id),
                group_id=str(group_id),
            )
            raise PermissionDeniedError
        self._group_repo.pin(user, group)
        log.debug('pin_group_success', group_id=str(group_id))
