"""Use case for ``PATCH /meetings/{id}/entries/{user_id}``.

Permission rules:

- The completed-meeting check fires BEFORE any role check, so a
  completed meeting is read-only for everyone (including MANAGER) per
  the openapi.yaml contract.
- MANAGER can edit any entry.
- MEMBER can edit only their own entry (``target_user_id == user.id``).
- GUEST cannot edit any entry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.meetings.logic.exceptions import (
    EntryNotFoundError,
    MeetingCompletedError,
    MeetingNotFoundError,
    PermissionDeniedError,
)
from server.apps.meetings.logic.value_objects import (
    MemberEntryPayload,
    MemberEntryUpdatePayload,
)

if TYPE_CHECKING:
    from uuid import UUID

    from server.apps.meetings.infra.mappers import MemberEntryMapper
    from server.apps.meetings.infra.repository import MeetingRepository
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class UpdateEntryUseCase:
    """Update a single member entry with role/owner/completed gating."""

    _meeting_repo: MeetingRepository
    _member_entry_mapper: MemberEntryMapper

    def __call__(
        self,
        user: User,
        meeting_id: UUID,
        target_user_id: UUID,
        payload: MemberEntryUpdatePayload,
    ) -> MemberEntryPayload:
        """Run the use case and return the updated payload."""
        log.debug(
            'update_entry_called',
            user_id=str(user.pk),
            meeting_id=str(meeting_id),
            target_user_id=str(target_user_id),
        )
        meeting = self._meeting_repo.get_by_id(meeting_id)
        if meeting is None:
            log.debug(
                'update_entry_meeting_not_found',
                meeting_id=str(meeting_id),
            )
            raise MeetingNotFoundError
        if meeting.completed:
            log.debug(
                'update_entry_meeting_completed',
                meeting_id=str(meeting_id),
            )
            raise MeetingCompletedError
        if user.role == 'MANAGER':
            log.debug('update_entry_manager_allowed')
        elif user.role == 'MEMBER' and target_user_id == user.id:
            log.debug('update_entry_member_self_allowed')
        else:
            log.debug(
                'update_entry_permission_denied',
                role=user.role,
                is_self=target_user_id == user.id,
            )
            raise PermissionDeniedError
        entry = self._meeting_repo.get_entry(meeting, target_user_id)
        if entry is None:
            log.debug(
                'update_entry_not_found',
                meeting_id=str(meeting_id),
                target_user_id=str(target_user_id),
            )
            raise EntryNotFoundError
        entry = self._meeting_repo.update_entry(
            entry,
            promised=payload.promised,
            done=payload.done,
            will_do=payload.will_do,
            discussion=payload.discussion,
            notes=payload.notes,
        )
        log.debug(
            'update_entry_success',
            entry_id=str(entry.id),
        )
        return self._member_entry_mapper.to_payload(entry)
