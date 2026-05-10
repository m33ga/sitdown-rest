"""Use case for ``DELETE /groups/{id}/members/{user_id}`` (MANAGER-only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.groups.logic.exceptions import (
    GroupNotFoundError,
    PermissionDeniedError,
)

if TYPE_CHECKING:
    from uuid import UUID

    from server.apps.groups.infra.repository import GroupRepository
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class RemoveMemberUseCase:
    """Remove a user from a project; MANAGER-only.

    Historical ``MemberEntry`` records are preserved by the database (no
    cascade on user removal at the membership level).
    """

    _group_repo: GroupRepository

    def __call__(
        self,
        user: User,
        group_id: UUID,
        target_user_id: UUID,
    ) -> None:
        """Run the use case.

        Propagates ``MemberNotFoundError`` from the repository for the
        controller to map to 404.
        """
        log.debug(
            'remove_member_called',
            user_id=str(user.id),
            group_id=str(group_id),
            target_user_id=str(target_user_id),
        )
        if user.role != 'MANAGER':
            log.debug('remove_member_permission_denied', role=user.role)
            raise PermissionDeniedError
        group = self._group_repo.get_by_id(group_id)
        if group is None:
            log.debug('remove_member_group_not_found', group_id=str(group_id))
            raise GroupNotFoundError
        self._group_repo.remove_member(group, target_user_id)
        log.debug(
            'remove_member_success',
            group_id=str(group_id),
            target_user_id=str(target_user_id),
        )
