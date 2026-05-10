"""Mappers between meetings ORM instances and value-object payloads."""

from __future__ import annotations

import attrs
import structlog

from server.apps.meetings.logic.value_objects import MeetingPayload
from server.apps.meetings.models import Meeting

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
