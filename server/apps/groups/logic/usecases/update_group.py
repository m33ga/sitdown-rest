"""Use case for ``PATCH /groups/{id}`` (MANAGER-only)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import attrs
import structlog

from server.apps.groups.infra.mappers import GroupMapper
from server.apps.groups.infra.repository import GroupRepository
from server.apps.groups.logic.exceptions import (
    GroupNotFoundError,
    PermissionDeniedError,
)
from server.apps.groups.logic.value_objects import (
    GroupCreatedPayload,
    GroupUpdatePayload,
)

if TYPE_CHECKING:
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class UpdateGroupUseCase:
    """Update a group's name; only MANAGER role is allowed."""

    _group_repo: GroupRepository
    _group_mapper: GroupMapper

    def __call__(
        self,
        user: User,
        group_id: UUID,
        payload: GroupUpdatePayload,
    ) -> GroupCreatedPayload:
        """Run the use case and return the updated group payload."""
        log.debug(
            'update_group_called',
            user_id=str(user.id),
            group_id=str(group_id),
        )
        if user.role != 'MANAGER':
            log.debug(
                'update_group_permission_denied',
                role=user.role,
            )
            raise PermissionDeniedError
        group = self._group_repo.get_by_id(group_id)
        if group is None:
            log.debug(
                'update_group_not_found',
                group_id=str(group_id),
            )
            raise GroupNotFoundError
        if payload.name is not None:
            group = self._group_repo.update(group, payload.name)
        log.debug('update_group_success', group_id=str(group.id))
        return self._group_mapper.to_created_payload(group)
