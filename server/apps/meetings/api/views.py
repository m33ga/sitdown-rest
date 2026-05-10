from __future__ import annotations

from http import HTTPStatus
from typing import final
from uuid import UUID

import structlog
from dmr import Body, Controller, modify
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.response import APIError

from server.apps.meetings.logic.exceptions import (
    GroupNotFoundError,
    MeetingDateConflictError,
    MeetingNotFoundError,
    PermissionDeniedError,
)
from server.apps.meetings.logic.usecases.create_meeting import (
    CreateMeetingUseCase,
)
from server.apps.meetings.logic.usecases.delete_meeting import (
    DeleteMeetingUseCase,
)
from server.apps.meetings.logic.usecases.list_meetings import (
    ListMeetingsUseCase,
)
from server.apps.meetings.logic.usecases.update_meeting import (
    UpdateMeetingUseCase,
)
from server.apps.meetings.logic.value_objects import (
    ErrorResponse,
    MeetingCreatePayload,
    MeetingPayload,
    MeetingUpdatePayload,
    MemberEntryPayload,
    MemberEntryUpdatePayload,
    PaginatedMeetingsPayload,
)
from server.common.di import HasContainer

log = structlog.get_logger()

_DEFAULT_PER_PAGE = 20
_MAX_PER_PAGE = 100


def _forbidden() -> APIError:
    return APIError(
        ErrorResponse(
            error='FORBIDDEN',
            message='You do not have permission to perform this action',
        ),
        status_code=HTTPStatus.FORBIDDEN,
    )


def _group_not_found(group_id: UUID) -> APIError:
    return APIError(
        ErrorResponse(
            error='NOT_FOUND',
            message=f"Group with id '{group_id}' does not exist",
        ),
        status_code=HTTPStatus.NOT_FOUND,
    )


def _meeting_not_found(meeting_id: UUID) -> APIError:
    return APIError(
        ErrorResponse(
            error='NOT_FOUND',
            message=f"Meeting with id '{meeting_id}' does not exist",
        ),
        status_code=HTTPStatus.NOT_FOUND,
    )


def _date_conflict() -> APIError:
    return APIError(
        ErrorResponse(
            error='CONFLICT',
            message='A meeting for this group and date already exists',
        ),
        status_code=HTTPStatus.CONFLICT,
    )


def _parse_int_param(
    raw: str | None,
    *,
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> int:
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


@final
class MeetingsCollection(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """GET /groups/{group_id}/meetings and POST /groups/{group_id}/meetings."""

    @modify(
        tags=['meetings'],
        status_code=HTTPStatus.OK,
        validate_responses=False,
    )
    def get(self) -> PaginatedMeetingsPayload:
        """List meetings for a group (sorted by date descending)."""
        group_id: UUID = self.kwargs['group_id']
        log.debug('meetings_list_called', group_id=str(group_id))
        page = _parse_int_param(
            self.request.GET.get('page'),
            default=1,
            minimum=1,
        )
        per_page = _parse_int_param(
            self.request.GET.get('per_page'),
            default=_DEFAULT_PER_PAGE,
            minimum=1,
            maximum=_MAX_PER_PAGE,
        )
        use_case = self.resolve(ListMeetingsUseCase)
        try:
            result = use_case(
                user=self.request.user,
                group_id=group_id,
                page=page,
                per_page=per_page,
            )
        except GroupNotFoundError:
            log.debug('meetings_list_not_found', group_id=str(group_id))
            raise _group_not_found(group_id) from None
        except PermissionDeniedError:
            log.debug('meetings_list_forbidden', group_id=str(group_id))
            raise _forbidden() from None
        log.debug(
            'meetings_list_done',
            group_id=str(group_id),
            total=result.total,
        )
        return result

    @modify(
        status_code=HTTPStatus.CREATED,
        tags=['meetings'],
        validate_responses=False,
    )
    def post(
        self,
        parsed_body: Body[MeetingCreatePayload],
    ) -> MeetingPayload:
        """Create a meeting (MANAGER only; eagerly creates MemberEntries)."""
        group_id: UUID = self.kwargs['group_id']
        log.debug(
            'meetings_create_called',
            group_id=str(group_id),
            date=str(parsed_body.date),
        )
        use_case = self.resolve(CreateMeetingUseCase)
        try:
            result = use_case(
                user=self.request.user,
                group_id=group_id,
                payload=parsed_body,
            )
        except PermissionDeniedError:
            log.debug('meetings_create_forbidden', group_id=str(group_id))
            raise _forbidden() from None
        except GroupNotFoundError:
            log.debug(
                'meetings_create_group_not_found',
                group_id=str(group_id),
            )
            raise _group_not_found(group_id) from None
        except MeetingDateConflictError:
            log.debug(
                'meetings_create_date_conflict',
                group_id=str(group_id),
                date=str(parsed_body.date),
            )
            raise _date_conflict() from None
        log.debug(
            'meetings_create_success',
            meeting_id=str(result.id),
        )
        return result


@final
class MeetingsDetail(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """PATCH /meetings/{id} and DELETE /meetings/{id}."""

    @modify(
        tags=['meetings'],
        status_code=HTTPStatus.OK,
        validate_responses=False,
    )
    def patch(
        self,
        parsed_body: Body[MeetingUpdatePayload],
    ) -> MeetingPayload:
        """Update meeting metadata (MANAGER only)."""
        meeting_id: UUID = self.kwargs['id']
        log.debug(
            'meetings_update_called',
            meeting_id=str(meeting_id),
        )
        use_case = self.resolve(UpdateMeetingUseCase)
        try:
            result = use_case(
                user=self.request.user,
                meeting_id=meeting_id,
                payload=parsed_body,
            )
        except PermissionDeniedError:
            log.debug('meetings_update_forbidden')
            raise _forbidden() from None
        except MeetingNotFoundError:
            log.debug(
                'meetings_update_not_found',
                meeting_id=str(meeting_id),
            )
            raise _meeting_not_found(meeting_id) from None
        except MeetingDateConflictError:
            log.debug(
                'meetings_update_date_conflict',
                meeting_id=str(meeting_id),
            )
            raise _date_conflict() from None
        log.debug(
            'meetings_update_success',
            meeting_id=str(meeting_id),
        )
        return result

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        tags=['meetings'],
        validate_responses=False,
    )
    def delete(self) -> None:
        """Delete a meeting and all its MemberEntries (MANAGER only)."""
        meeting_id: UUID = self.kwargs['id']
        log.debug(
            'meetings_delete_called',
            meeting_id=str(meeting_id),
        )
        use_case = self.resolve(DeleteMeetingUseCase)
        try:
            use_case(user=self.request.user, meeting_id=meeting_id)
        except PermissionDeniedError:
            log.debug('meetings_delete_forbidden')
            raise _forbidden() from None
        except MeetingNotFoundError:
            log.debug(
                'meetings_delete_not_found',
                meeting_id=str(meeting_id),
            )
            raise _meeting_not_found(meeting_id) from None
        log.debug(
            'meetings_delete_success',
            meeting_id=str(meeting_id),
        )


@final
class EntriesCollection(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """GET /meetings/{id}/entries."""

    @modify(tags=['entries'])
    def get(self) -> list[MemberEntryPayload]:
        """List all member entries for a meeting (newest updated first)."""
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
        """Update a member entry (MEMBER: own; MANAGER: any; r/o if done)."""
        raise NotImplementedError
