"""Use case for ``GET /groups/{group_id}/meetings``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.meetings.logic.exceptions import (
    GroupNotFoundError,
    PermissionDeniedError,
)
from server.apps.meetings.logic.value_objects import PaginatedMeetingsPayload

if TYPE_CHECKING:
    from uuid import UUID

    from server.apps.meetings.infra.mappers import MeetingMapper
    from server.apps.meetings.infra.repository import MeetingRepository
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class ListMeetingsUseCase:
    """List meetings for a group, gated by group access."""

    _meeting_repo: MeetingRepository
    _meeting_mapper: MeetingMapper

    def __call__(
        self,
        user: User,
        group_id: UUID,
        page: int,
        per_page: int,
    ) -> PaginatedMeetingsPayload:
        """Run the use case and return a paginated payload."""
        log.debug(
            'list_meetings_called',
            user_id=str(user.pk),
            group_id=str(group_id),
            page=page,
            per_page=per_page,
        )
        group = self._meeting_repo.get_group(group_id)
        if group is None:
            log.debug(
                'list_meetings_group_not_found',
                group_id=str(group_id),
            )
            raise GroupNotFoundError
        if not self._meeting_repo.has_access(user, user.role, group):
            log.debug(
                'list_meetings_access_denied',
                user_id=str(user.pk),
                group_id=str(group_id),
            )
            raise PermissionDeniedError
        meetings, total = self._meeting_repo.list_for_group(
            group=group,
            page=page,
            per_page=per_page,
        )
        results = [
            self._meeting_mapper.to_payload(meeting)
            for meeting in meetings
        ]
        log.debug(
            'list_meetings_done',
            count=len(results),
            total=total,
        )
        return PaginatedMeetingsPayload(
            results=results,
            total=total,
            page=page,
            per_page=per_page,
        )
