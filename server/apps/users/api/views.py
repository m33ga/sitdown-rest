from http import HTTPStatus
from typing import final

import structlog
from dmr import Body, Controller, modify
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.response import APIError

from server.apps.users.logic.exceptions import AuthenticationError, InvalidRefreshTokenError
from server.apps.users.logic.usecases.create_tokens import CreateTokensUseCase
from server.apps.users.logic.usecases.refresh_tokens import RefreshTokensUseCase
from server.apps.users.logic.value_objects import (
    ErrorResponse,
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

    @modify(tags=['auth'], status_code=HTTPStatus.OK, validate_responses=False)
    def post(
        self,
        parsed_body: Body[TokenCreatePayload],
    ) -> TokenResponse:
        """Authenticate with username and password."""
        log.debug('token_create_called')
        use_case = self.resolve(CreateTokensUseCase)
        try:
            return use_case(parsed_body)
        except AuthenticationError:
            log.debug('token_create_auth_failed')
            raise APIError(
                ErrorResponse(
                    error='INVALID_CREDENTIALS',
                    message='Invalid username or password',
                ),
                status_code=HTTPStatus.UNAUTHORIZED,
            )


@final
class TokenRefresh(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """POST /token/refresh — exchange refresh token for a new pair."""

    @modify(tags=['auth'], status_code=HTTPStatus.OK, validate_responses=False)
    def post(
        self,
        parsed_body: Body[TokenRefreshPayload],
    ) -> TokenRefreshResponse:
        """Rotate the refresh token and issue a new access JWT."""
        log.debug('token_refresh_called')
        use_case = self.resolve(RefreshTokensUseCase)
        try:
            return use_case(parsed_body)
        except InvalidRefreshTokenError:
            log.debug('token_refresh_failed')
            raise APIError(
                ErrorResponse(
                    error='INVALID_REFRESH_TOKEN',
                    message='Refresh token is invalid or has expired',
                ),
                status_code=HTTPStatus.UNAUTHORIZED,
            )


@final
class UsersList(
    HasContainer,
    Controller[MsgspecSerializer],
):
    """GET /users — paginated organisation user directory (MANAGER only)."""

    @modify(status_code=HTTPStatus.OK, tags=['users'])
    def get(self) -> PaginatedUsersPayload:
        """Return a paginated, searchable list of org users."""
        raise NotImplementedError
