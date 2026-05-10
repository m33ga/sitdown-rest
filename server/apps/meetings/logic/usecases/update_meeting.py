"""Use case for ``PATCH /meetings/{id}`` (MANAGER-only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.meetings.logic.exceptions import (
    MeetingNotFoundError,
    PermissionDeniedError,
)
from server.apps.meetings.logic.value_objects import (
    MeetingPayload,
    MeetingUpdatePayload,
)

if TYPE_CHECKING:
    from uuid import UUID

    from server.apps.meetings.infra.mappers import MeetingMapper
    from server.apps.meetings.infra.repository import MeetingRepository
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class UpdateMeetingUseCase:
    """Update meeting metadata (title / date / completed); MANAGER-only."""

    _meeting_repo: MeetingRepository
    _meeting_mapper: MeetingMapper

    def __call__(
        self,
        user: User,
        meeting_id: UUID,
        payload: MeetingUpdatePayload,
    ) -> MeetingPayload:
        """Run the use case; propagates ``MeetingDateConflictError`` for 409."""
        log.debug(
            'update_meeting_called',
            user_id=str(user.pk),
            meeting_id=str(meeting_id),
        )
        if user.role != 'MANAGER':
            log.debug('update_meeting_permission_denied', role=user.role)
            raise PermissionDeniedError
        meeting = self._meeting_repo.get_by_id(meeting_id)
        if meeting is None:
            log.debug(
                'update_meeting_not_found',
                meeting_id=str(meeting_id),
            )
            raise MeetingNotFoundError
        meeting = self._meeting_repo.update(
            meeting,
            title=payload.title,
            date=payload.date,
            completed=payload.completed,
        )
        log.debug(
            'update_meeting_success',
            meeting_id=str(meeting.id),
        )
        return self._meeting_mapper.to_payload(meeting)
