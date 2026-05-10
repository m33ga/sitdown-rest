"""Use case for ``POST /groups/{id}/members`` (MANAGER-only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.groups.logic.exceptions import (
    GroupNotFoundError,
    PermissionDeniedError,
)
from server.apps.groups.logic.value_objects import (
    AddMemberPayload,
    ProjectMemberRecordPayload,
)

if TYPE_CHECKING:
    from uuid import UUID

    from server.apps.groups.infra.mappers import ProjectMemberMapper
    from server.apps.groups.infra.repository import GroupRepository
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class AddMemberUseCase:
    """Add a user to a project as a ProjectMember; MANAGER-only."""

    _group_repo: GroupRepository
    _project_member_mapper: ProjectMemberMapper

    def __call__(
        self,
        user: User,
        group_id: UUID,
        payload: AddMemberPayload,
    ) -> ProjectMemberRecordPayload:
        """Run the use case and return the created member payload.

        Propagates ``UserNotFoundError`` and ``MemberAlreadyExistsError``
        from the repository for the controller to map to 404 and 409.
        """
        log.debug(
            'add_member_called',
            user_id=str(user.id),
            group_id=str(group_id),
            target_user_id=str(payload.user_id),
        )
        if user.role != 'MANAGER':
            log.debug('add_member_permission_denied', role=user.role)
            raise PermissionDeniedError
        group = self._group_repo.get_by_id(group_id)
        if group is None:
            log.debug('add_member_group_not_found', group_id=str(group_id))
            raise GroupNotFoundError
        member = self._group_repo.add_member(group, payload.user_id)
        log.debug(
            'add_member_success',
            membership_id=str(member.id),
            user_id=str(member.user_id),
        )
        return self._project_member_mapper.to_payload(member)
