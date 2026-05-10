from __future__ import annotations

from http import HTTPStatus
from typing import final
from uuid import UUID

import structlog
from dmr import Body, Controller, modify
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.response import APIError

from server.apps.groups.logic.exceptions import (
    GroupNotFoundError,
    PermissionDeniedError,
)
from server.apps.groups.logic.usecases.create_group import CreateGroupUseCase
from server.apps.groups.logic.usecases.delete_group import DeleteGroupUseCase
from server.apps.groups.logic.usecases.list_groups import ListGroupsUseCase
from server.apps.groups.logic.usecases.pin_group import PinGroupUseCase
from server.apps.groups.logic.usecases.unpin_group import UnpinGroupUseCase
from server.apps.groups.logic.usecases.update_group import UpdateGroupUseCase
from server.apps.groups.logic.value_objects import (
    AddMemberPayload,
    ErrorResponse,
    GroupCreatedPayload,
    GroupCreatePayload,
    GroupUpdatePayload,
    PaginatedGroupsPayload,
    ProjectMemberRecordPayload,
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


def _not_found(group_id: UUID) -> APIError:
    return APIError(
        ErrorResponse(
            error='NOT_FOUND',
            message=f"Group with id '{group_id}' does not exist",
        ),
        status_code=HTTPStatus.NOT_FOUND,
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
class GroupsCollection(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """GET /groups and POST /groups."""

    @modify(
        tags=['groups'],
        status_code=HTTPStatus.OK,
        validate_responses=False,
    )
    def get(self) -> PaginatedGroupsPayload:
        """List accessible groups (pinned first)."""
        log.debug('groups_list_called')
        search = self.request.GET.get('search') or None
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
        use_case = self.resolve(ListGroupsUseCase)
        result = use_case(
            user=self.request.user,
            search=search,
            page=page,
            per_page=per_page,
        )
        log.debug('groups_list_done', total=result.total)
        return result

    @modify(
        status_code=HTTPStatus.CREATED,
        tags=['groups'],
        validate_responses=False,
    )
    def post(
        self,
        parsed_body: Body[GroupCreatePayload],
    ) -> GroupCreatedPayload:
        """Create a new project group (MANAGER only)."""
        log.debug('groups_create_called')
        use_case = self.resolve(CreateGroupUseCase)
        try:
            result = use_case(user=self.request.user, payload=parsed_body)
        except PermissionDeniedError:
            log.debug('groups_create_forbidden')
            raise _forbidden() from None
        log.debug('groups_create_success', group_id=str(result.id))
        return result


@final
class GroupsDetail(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """PATCH /groups/{id} and DELETE /groups/{id}."""

    @modify(
        tags=['groups'],
        status_code=HTTPStatus.OK,
        validate_responses=False,
    )
    def patch(
        self,
        parsed_body: Body[GroupUpdatePayload],
    ) -> GroupCreatedPayload:
        """Update a group's name (MANAGER only)."""
        group_id: UUID = self.kwargs['id']
        log.debug('groups_update_called', group_id=str(group_id))
        use_case = self.resolve(UpdateGroupUseCase)
        try:
            result = use_case(
                user=self.request.user,
                group_id=group_id,
                payload=parsed_body,
            )
        except PermissionDeniedError:
            log.debug('groups_update_forbidden')
            raise _forbidden() from None
        except GroupNotFoundError:
            log.debug('groups_update_not_found', group_id=str(group_id))
            raise _not_found(group_id) from None
        log.debug('groups_update_success', group_id=str(group_id))
        return result

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        tags=['groups'],
        validate_responses=False,
    )
    def delete(self) -> None:
        """Delete a group and all its meetings (MANAGER only)."""
        group_id: UUID = self.kwargs['id']
        log.debug('groups_delete_called', group_id=str(group_id))
        use_case = self.resolve(DeleteGroupUseCase)
        try:
            use_case(user=self.request.user, group_id=group_id)
        except PermissionDeniedError:
            log.debug('groups_delete_forbidden')
            raise _forbidden() from None
        except GroupNotFoundError:
            log.debug('groups_delete_not_found', group_id=str(group_id))
            raise _not_found(group_id) from None
        log.debug('groups_delete_success', group_id=str(group_id))


@final
class GroupsPin(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """PUT /groups/{id}/pin and DELETE /groups/{id}/pin."""

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        tags=['groups'],
        validate_responses=False,
    )
    def put(self) -> None:
        """Pin a group for the requesting user (idempotent)."""
        group_id: UUID = self.kwargs['id']
        log.debug('groups_pin_called', group_id=str(group_id))
        use_case = self.resolve(PinGroupUseCase)
        try:
            use_case(user=self.request.user, group_id=group_id)
        except GroupNotFoundError:
            log.debug('groups_pin_not_found', group_id=str(group_id))
            raise _not_found(group_id) from None
        except PermissionDeniedError:
            log.debug('groups_pin_forbidden', group_id=str(group_id))
            raise _forbidden() from None
        log.debug('groups_pin_success', group_id=str(group_id))

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        tags=['groups'],
        validate_responses=False,
    )
    def delete(self) -> None:
        """Unpin a group for the requesting user (idempotent)."""
        group_id: UUID = self.kwargs['id']
        log.debug('groups_unpin_called', group_id=str(group_id))
        use_case = self.resolve(UnpinGroupUseCase)
        try:
            use_case(user=self.request.user, group_id=group_id)
        except GroupNotFoundError:
            log.debug('groups_unpin_not_found', group_id=str(group_id))
            raise _not_found(group_id) from None
        except PermissionDeniedError:
            log.debug('groups_unpin_forbidden', group_id=str(group_id))
            raise _forbidden() from None
        log.debug('groups_unpin_success', group_id=str(group_id))


@final
class GroupsMembersCollection(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """GET /groups/{id}/members and POST /groups/{id}/members."""

    @modify(tags=['members'])
    def get(self) -> list[ProjectMemberRecordPayload]:
        """List all project members."""
        raise NotImplementedError

    @modify(status_code=HTTPStatus.CREATED, tags=['members'])
    def post(
        self,
        parsed_body: Body[AddMemberPayload],
    ) -> ProjectMemberRecordPayload:
        """Add a user to the project (MANAGER only)."""
        raise NotImplementedError


@final
class GroupsMembersDetail(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """DELETE /groups/{id}/members/{user_id}."""

    @modify(status_code=HTTPStatus.NO_CONTENT, tags=['members'])
    def delete(self) -> None:
        """Remove a user from the project (MANAGER only)."""
        raise NotImplementedError
