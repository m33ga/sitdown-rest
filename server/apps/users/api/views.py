from http import HTTPStatus
from typing import final

import structlog
from dmr import Body, Controller, modify
from dmr.plugins.msgspec import MsgspecSerializer

from server.apps.users.logic.value_objects import (
    PaginatedUsersPayload,
    TokenCreatePayload,
    TokenRefreshPayload,
    TokenRefreshResponse,
    TokenResponse,
)
from server.common.di import HasContainer

log = structlog.get_logger()


@final
class TokenCreate(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """POST /token — issue a new access/refresh token pair."""

    def post(
        self,
        parsed_body: Body[TokenCreatePayload],
    ) -> TokenResponse:
        """Authenticate with username and password."""
        log.debug('token_create_called')
        raise NotImplementedError


@final
class TokenRefresh(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """POST /token/refresh — exchange refresh token for a new pair."""

    def post(
        self,
        parsed_body: Body[TokenRefreshPayload],
    ) -> TokenRefreshResponse:
        """Rotate the refresh token and issue a new access JWT."""
        log.debug('token_refresh_called')
        raise NotImplementedError


@final
class UsersList(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """GET /users — paginated organisation user directory (MANAGER only)."""

    @modify(status_code=HTTPStatus.OK)
    def get(self) -> PaginatedUsersPayload:
        """Return a paginated, searchable list of org users."""
        log.debug('users_list_called')
        raise NotImplementedError
