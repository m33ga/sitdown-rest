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
    MemberAlreadyExistsError,
    MemberNotFoundError,
    PermissionDeniedError,
    UserNotFoundError,
)
from server.apps.groups.logic.usecases.add_member import AddMemberUseCase
from server.apps.groups.logic.usecases.create_group import CreateGroupUseCase
from server.apps.groups.logic.usecases.delete_group import DeleteGroupUseCase
from server.apps.groups.logic.usecases.list_groups import ListGroupsUseCase
from server.apps.groups.logic.usecases.list_members import ListMembersUseCase
from server.apps.groups.logic.usecases.pin_group import PinGroupUseCase
from server.apps.groups.logic.usecases.remove_member import (
    RemoveMemberUseCase,
)
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


def _user_not_found(user_id: UUID) -> APIError:
    return APIError(
        ErrorResponse(
            error='NOT_FOUND',
            message=f"User with id '{user_id}' does not exist",
        ),
        status_code=HTTPStatus.NOT_FOUND,
    )


def _member_not_found(user_id: UUID) -> APIError:
    return APIError(
        ErrorResponse(
            error='NOT_FOUND',
            message=(
                f"User with id '{user_id}' is not a member of this group"
            ),
        ),
        status_code=HTTPStatus.NOT_FOUND,
    )


def _conflict() -> APIError:
    return APIError(
        ErrorResponse(
            error='CONFLICT',
            message='User is already a member of this group',
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

    @modify(
        tags=['members'],
        status_code=HTTPStatus.OK,
        validate_responses=False,
    )
    def get(self) -> list[ProjectMemberRecordPayload]:
        """List all project members of a group."""
        group_id: UUID = self.kwargs['id']
        log.debug('members_list_called', group_id=str(group_id))
        use_case = self.resolve(ListMembersUseCase)
        try:
            result = use_case(user=self.request.user, group_id=group_id)
        except PermissionDeniedError:
            log.debug('members_list_forbidden', group_id=str(group_id))
            raise _forbidden() from None
        except GroupNotFoundError:
            log.debug('members_list_not_found', group_id=str(group_id))
            raise _not_found(group_id) from None
        log.debug(
            'members_list_done',
            group_id=str(group_id),
            count=len(result),
        )
        return result

    @modify(
        status_code=HTTPStatus.CREATED,
        tags=['members'],
        validate_responses=False,
    )
    def post(
        self,
        parsed_body: Body[AddMemberPayload],
    ) -> ProjectMemberRecordPayload:
        """Add a user to the project (MANAGER only)."""
        group_id: UUID = self.kwargs['id']
        log.debug(
            'members_add_called',
            group_id=str(group_id),
            target_user_id=str(parsed_body.user_id),
        )
        use_case = self.resolve(AddMemberUseCase)
        try:
            result = use_case(
                user=self.request.user,
                group_id=group_id,
                payload=parsed_body,
            )
        except PermissionDeniedError:
            log.debug('members_add_forbidden', group_id=str(group_id))
            raise _forbidden() from None
        except GroupNotFoundError:
            log.debug('members_add_group_not_found', group_id=str(group_id))
            raise _not_found(group_id) from None
        except UserNotFoundError:
            log.debug(
                'members_add_user_not_found',
                target_user_id=str(parsed_body.user_id),
            )
            raise _user_not_found(parsed_body.user_id) from None
        except MemberAlreadyExistsError:
            log.debug(
                'members_add_duplicate',
                group_id=str(group_id),
                target_user_id=str(parsed_body.user_id),
            )
            raise _conflict() from None
        log.debug(
            'members_add_success',
            group_id=str(group_id),
            target_user_id=str(parsed_body.user_id),
        )
        return result


@final
class GroupsMembersDetail(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """DELETE /groups/{id}/members/{user_id}."""

    @modify(
        status_code=HTTPStatus.NO_CONTENT,
        tags=['members'],
        validate_responses=False,
    )
    def delete(self) -> None:
        """Remove a user from the project (MANAGER only)."""
        group_id: UUID = self.kwargs['id']
        target_user_id: UUID = self.kwargs['user_id']
        log.debug(
            'members_remove_called',
            group_id=str(group_id),
            target_user_id=str(target_user_id),
        )
        use_case = self.resolve(RemoveMemberUseCase)
        try:
            use_case(
                user=self.request.user,
                group_id=group_id,
                target_user_id=target_user_id,
            )
        except PermissionDeniedError:
            log.debug('members_remove_forbidden', group_id=str(group_id))
            raise _forbidden() from None
        except GroupNotFoundError:
            log.debug(
                'members_remove_group_not_found',
                group_id=str(group_id),
            )
            raise _not_found(group_id) from None
        except MemberNotFoundError:
            log.debug(
                'members_remove_user_not_a_member',
                target_user_id=str(target_user_id),
            )
            raise _member_not_found(target_user_id) from None
        log.debug(
            'members_remove_success',
            group_id=str(group_id),
            target_user_id=str(target_user_id),
        )
