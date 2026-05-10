"""Use case for ``GET /groups/{id}/members``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.groups.logic.exceptions import (
    GroupNotFoundError,
    PermissionDeniedError,
)
from server.apps.groups.logic.value_objects import ProjectMemberRecordPayload

if TYPE_CHECKING:
    from uuid import UUID

    from server.apps.groups.infra.mappers import ProjectMemberMapper
    from server.apps.groups.infra.repository import GroupRepository
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class ListMembersUseCase:
    """List the project members of a group, gated by access."""

    _group_repo: GroupRepository
    _project_member_mapper: ProjectMemberMapper

    def __call__(
        self,
        user: User,
        group_id: UUID,
    ) -> list[ProjectMemberRecordPayload]:
        """Return the membership list; raises if missing or forbidden."""
        log.debug(
            'list_members_called',
            user_id=str(user.id),
            group_id=str(group_id),
        )
        group = self._group_repo.get_by_id(group_id)
        if group is None:
            log.debug('list_members_group_not_found', group_id=str(group_id))
            raise GroupNotFoundError
        if (
            user.role != 'MANAGER'
            and not self._group_repo.is_member(user, group)
        ):
            log.debug(
                'list_members_access_denied',
                user_id=str(user.id),
                group_id=str(group_id),
            )
            raise PermissionDeniedError
        members = self._group_repo.list_members(group)
        results = [
            self._project_member_mapper.to_payload(member)
            for member in members
        ]
        log.debug('list_members_done', count=len(results))
        return results
