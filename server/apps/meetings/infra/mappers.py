"""Mappers between meetings ORM instances and value-object payloads."""

from __future__ import annotations

import attrs
import structlog

from server.apps.meetings.logic.value_objects import (
    MeetingPayload,
    MemberEntryPayload,
)
from server.apps.meetings.models import Meeting, MemberEntry

log = structlog.get_logger()


@attrs.define(slots=True, frozen=True)
class MeetingMapper:
    """Translate ``Meeting`` ORM instances into msgspec response payloads."""

    def to_payload(self, meeting: Meeting) -> MeetingPayload:
        """Map a ``Meeting`` to its API response payload."""
        log.debug(
            'meeting_mapper_to_payload_called',
            meeting_id=str(meeting.id),
        )
        return MeetingPayload(
            id=meeting.id,
            group_id=meeting.group_id,
            title=meeting.title,
            date=meeting.date,
            completed=meeting.completed,
        )


@attrs.define(slots=True, frozen=True)
class MemberEntryMapper:
    """Translate ``MemberEntry`` ORM rows into msgspec response payloads."""

    def to_payload(self, entry: MemberEntry) -> MemberEntryPayload:
        """Map a ``MemberEntry`` to its API response payload."""
        log.debug(
            'member_entry_mapper_to_payload_called',
            entry_id=str(entry.id),
        )
        return MemberEntryPayload(
            id=entry.id,
            meeting_id=entry.meeting_id,
            user_id=entry.user_id,
            updated_at=entry.updated_at,
            promised=entry.promised,
            done=entry.done,
            will_do=entry.will_do,
            discussion=entry.discussion,
            notes=entry.notes,
        )
