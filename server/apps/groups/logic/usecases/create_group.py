"""Use case for ``POST /groups`` (MANAGER-only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.groups.infra.mappers import GroupMapper
from server.apps.groups.infra.repository import GroupRepository
from server.apps.groups.logic.exceptions import PermissionDeniedError
from server.apps.groups.logic.value_objects import (
    GroupCreatedPayload,
    GroupCreatePayload,
)

if TYPE_CHECKING:
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class CreateGroupUseCase:
    """Create a new group; only MANAGER role is allowed."""

    _group_repo: GroupRepository
    _group_mapper: GroupMapper

    def __call__(
        self,
        user: User,
        payload: GroupCreatePayload,
    ) -> GroupCreatedPayload:
        """Run the use case and return the created group payload."""
        log.debug('create_group_called', user_id=str(user.id))
        if user.role != 'MANAGER':
            log.debug(
                'create_group_permission_denied',
                role=user.role,
            )
            raise PermissionDeniedError
        group = self._group_repo.create(payload.name)
        log.debug('create_group_success', group_id=str(group.id))
        return self._group_mapper.to_created_payload(group)
