from http import HTTPStatus
from typing import final

import structlog
from dmr import Body, Controller, modify
from dmr.plugins.msgspec import MsgspecSerializer

from server.apps.groups.logic.value_objects import (
    AddMemberPayload,
    GroupCreatePayload,
    GroupCreatedPayload,
    GroupUpdatePayload,
    PaginatedGroupsPayload,
    ProjectMemberRecordPayload,
)
from server.common.di import HasContainer

log = structlog.get_logger()


@final
class GroupsCollection(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """GET /groups and POST /groups."""

    @modify(tags=['groups'])
    def get(self) -> PaginatedGroupsPayload:
        """List accessible groups (pinned first)."""
        raise NotImplementedError

    @modify(status_code=HTTPStatus.CREATED, tags=['groups'])
    def post(
        self,
        parsed_body: Body[GroupCreatePayload],
    ) -> GroupCreatedPayload:
        """Create a new project group (MANAGER only)."""
        raise NotImplementedError


@final
class GroupsDetail(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """PATCH /groups/{id} and DELETE /groups/{id}."""

    @modify(tags=['groups'])
    def patch(
        self,
        parsed_body: Body[GroupUpdatePayload],
    ) -> GroupCreatedPayload:
        """Update a group's name (MANAGER only)."""
        raise NotImplementedError

    @modify(status_code=HTTPStatus.NO_CONTENT, tags=['groups'])
    def delete(self) -> None:
        """Delete a group and all its meetings (MANAGER only)."""
        raise NotImplementedError


@final
class GroupsPin(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """PUT /groups/{id}/pin and DELETE /groups/{id}/pin."""

    @modify(status_code=HTTPStatus.NO_CONTENT, tags=['groups'])
    def put(self) -> None:
        """Pin a group for the requesting user (idempotent)."""
        raise NotImplementedError

    @modify(status_code=HTTPStatus.NO_CONTENT, tags=['groups'])
    def delete(self) -> None:
        """Unpin a group for the requesting user (idempotent)."""
        raise NotImplementedError


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
