"""Use case for ``POST /groups/{group_id}/meetings`` (MANAGER-only)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.meetings.logic.exceptions import (
    GroupNotFoundError,
    PermissionDeniedError,
)
from server.apps.meetings.logic.value_objects import (
    MeetingCreatePayload,
    MeetingPayload,
)

if TYPE_CHECKING:
    from uuid import UUID

    from server.apps.meetings.infra.mappers import MeetingMapper
    from server.apps.meetings.infra.repository import MeetingRepository
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class CreateMeetingUseCase:
    """Create a meeting + eager MemberEntry rows; MANAGER-only.

    If ``payload.title`` is missing or whitespace-only, the use case
    auto-generates ``f'standup · {date}'`` (matches the openapi.yaml
    example).
    """

    _meeting_repo: MeetingRepository
    _meeting_mapper: MeetingMapper

    def __call__(
        self,
        user: User,
        group_id: UUID,
        payload: MeetingCreatePayload,
    ) -> MeetingPayload:
        """Run the use case; propagate ``MeetingDateConflictError`` for 409."""
        log.debug(
            'create_meeting_called',
            user_id=str(user.pk),
            group_id=str(group_id),
            date=str(payload.date),
        )
        if user.role != 'MANAGER':
            log.debug('create_meeting_permission_denied', role=user.role)
            raise PermissionDeniedError
        group = self._meeting_repo.get_group(group_id)
        if group is None:
            log.debug(
                'create_meeting_group_not_found',
                group_id=str(group_id),
            )
            raise GroupNotFoundError
        title = payload.title.strip() if payload.title else ''
        if not title:
            title = f'standup · {payload.date}'
            log.debug('create_meeting_title_defaulted', title=title)
        meeting = self._meeting_repo.create_with_entries(
            group=group,
            title=title,
            date=payload.date,
        )
        log.debug(
            'create_meeting_success',
            meeting_id=str(meeting.id),
        )
        return self._meeting_mapper.to_payload(meeting)
