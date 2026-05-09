from http import HTTPStatus
from typing import final

import structlog
from dmr import Body, Controller, modify
from dmr.plugins.msgspec import MsgspecSerializer

from server.apps.meetings.logic.value_objects import (
    MeetingCreatePayload,
    MeetingPayload,
    MeetingUpdatePayload,
    MemberEntryPayload,
    MemberEntryUpdatePayload,
    PaginatedMeetingsPayload,
)
from server.common.di import HasContainer

log = structlog.get_logger()


@final
class MeetingsCollection(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """GET /groups/{group_id}/meetings and POST /groups/{group_id}/meetings."""

    @modify(tags=['meetings'])
    def get(self) -> PaginatedMeetingsPayload:
        """List meetings for a group (sorted by date descending)."""
        log.debug('meetings_list_called', group_id=self.kwargs.get('group_id'))
        raise NotImplementedError

    @modify(status_code=HTTPStatus.CREATED, tags=['meetings'])
    def post(
        self,
        parsed_body: Body[MeetingCreatePayload],
    ) -> MeetingPayload:
        """Create a standup meeting (MANAGER only; eagerly creates MemberEntries)."""
        log.debug('meetings_create_called', group_id=self.kwargs.get('group_id'))
        raise NotImplementedError


@final
class MeetingsDetail(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """PATCH /meetings/{id} and DELETE /meetings/{id}."""

    @modify(tags=['meetings'])
    def patch(
        self,
        parsed_body: Body[MeetingUpdatePayload],
    ) -> MeetingPayload:
        """Update meeting metadata (MANAGER only)."""
        log.debug('meetings_update_called', meeting_id=self.kwargs.get('id'))
        raise NotImplementedError

    @modify(status_code=HTTPStatus.NO_CONTENT, tags=['meetings'])
    def delete(self) -> None:
        """Delete a meeting and all its MemberEntries (MANAGER only)."""
        log.debug('meetings_destroy_called', meeting_id=self.kwargs.get('id'))
        raise NotImplementedError


@final
class EntriesCollection(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """GET /meetings/{id}/entries."""

    @modify(tags=['entries'])
    def get(self) -> list[MemberEntryPayload]:
        """List all member entries for a meeting (ordered by updated_at desc)."""
        log.debug('entries_list_called', meeting_id=self.kwargs.get('id'))
        raise NotImplementedError


@final
class EntriesDetail(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """PATCH /meetings/{id}/entries/{user_id}."""

    @modify(tags=['entries'])
    def patch(
        self,
        parsed_body: Body[MemberEntryUpdatePayload],
    ) -> MemberEntryPayload:
        """Update a member entry (MEMBER: own only; MANAGER: any; read-only if completed)."""
        log.debug(
            'entries_update_called',
            meeting_id=self.kwargs.get('id'),
            user_id=self.kwargs.get('user_id'),
        )
        raise NotImplementedError
