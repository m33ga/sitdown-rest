"""Use case for ``DELETE /meetings/{id}`` (MANAGER-only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.meetings.logic.exceptions import (
    MeetingNotFoundError,
    PermissionDeniedError,
)

if TYPE_CHECKING:
    from uuid import UUID

    from server.apps.meetings.infra.repository import MeetingRepository
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class DeleteMeetingUseCase:
    """Delete a meeting and cascade-remove its MemberEntry rows."""

    _meeting_repo: MeetingRepository

    def __call__(self, user: User, meeting_id: UUID) -> None:
        """Run the use case; raises if non-MANAGER or meeting missing."""
        log.debug(
            'delete_meeting_called',
            user_id=str(user.pk),
            meeting_id=str(meeting_id),
        )
        if user.role != 'MANAGER':
            log.debug('delete_meeting_permission_denied', role=user.role)
            raise PermissionDeniedError
        meeting = self._meeting_repo.get_by_id(meeting_id)
        if meeting is None:
            log.debug(
                'delete_meeting_not_found',
                meeting_id=str(meeting_id),
            )
            raise MeetingNotFoundError
        self._meeting_repo.delete(meeting)
        log.debug(
            'delete_meeting_success',
            meeting_id=str(meeting_id),
        )
