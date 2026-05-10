"""Use case for ``DELETE /groups/{id}`` (MANAGER-only)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import attrs
import structlog

from server.apps.groups.infra.repository import GroupRepository
from server.apps.groups.logic.exceptions import (
    GroupNotFoundError,
    PermissionDeniedError,
)

if TYPE_CHECKING:
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class DeleteGroupUseCase:
    """Delete a group and cascade-remove its meetings and members."""

    _group_repo: GroupRepository

    def __call__(self, user: User, group_id: UUID) -> None:
        """Run the use case; raises if non-MANAGER or group is missing."""
        log.debug(
            'delete_group_called',
            user_id=str(user.id),
            group_id=str(group_id),
        )
        if user.role != 'MANAGER':
            log.debug(
                'delete_group_permission_denied',
                role=user.role,
            )
            raise PermissionDeniedError
        group = self._group_repo.get_by_id(group_id)
        if group is None:
            log.debug(
                'delete_group_not_found',
                group_id=str(group_id),
            )
            raise GroupNotFoundError
        self._group_repo.delete(group)
        log.debug('delete_group_success', group_id=str(group_id))
