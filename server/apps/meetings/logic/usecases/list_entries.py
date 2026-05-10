"""Use case for ``GET /meetings/{id}/entries``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.meetings.logic.exceptions import (
    MeetingNotFoundError,
    PermissionDeniedError,
)
from server.apps.meetings.logic.value_objects import MemberEntryPayload

if TYPE_CHECKING:
    from uuid import UUID

    from server.apps.meetings.infra.mappers import MemberEntryMapper
    from server.apps.meetings.infra.repository import MeetingRepository
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class ListEntriesUseCase:
    """List the member entries for a meeting; gated by group access."""

    _meeting_repo: MeetingRepository
    _member_entry_mapper: MemberEntryMapper

    def __call__(
        self,
        user: User,
        meeting_id: UUID,
    ) -> list[MemberEntryPayload]:
        """Return the entries; raises if missing or forbidden."""
        log.debug(
            'list_entries_called',
            user_id=str(user.pk),
            meeting_id=str(meeting_id),
        )
        meeting = self._meeting_repo.get_by_id(meeting_id)
        if meeting is None:
            log.debug(
                'list_entries_meeting_not_found',
                meeting_id=str(meeting_id),
            )
            raise MeetingNotFoundError
        if not self._meeting_repo.has_access(
            user,
            user.role,
            meeting.group,
        ):
            log.debug(
                'list_entries_access_denied',
                user_id=str(user.pk),
                meeting_id=str(meeting_id),
            )
            raise PermissionDeniedError
        entries = self._meeting_repo.list_entries_for_meeting(meeting)
        results = [
            self._member_entry_mapper.to_payload(entry)
            for entry in entries
        ]
        log.debug(
            'list_entries_done',
            meeting_id=str(meeting_id),
            count=len(results),
        )
        return results
