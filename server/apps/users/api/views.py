from __future__ import annotations

import datetime as dt
from http import HTTPStatus
from typing import TYPE_CHECKING, final, override

import structlog
from dmr import Body, Controller, ResponseSpec, modify
from dmr.exceptions import NotAuthenticatedError
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security.jwt.views import (
    ObtainTokensPayload,
    ObtainTokensResponse,
    ObtainTokensSyncController,
    RefreshTokenPayload,
    RefreshTokenSyncController,
)

from server.apps.users.logic.value_objects import (
    ErrorResponse,
    PaginatedUsersPayload,
)
from server.common.di import HasContainer

if TYPE_CHECKING:
    from django.http import HttpResponse
    from dmr.endpoint import Endpoint

log = structlog.get_logger()

_ACCESS_EXPIRY = dt.timedelta(seconds=60)
_REFRESH_EXPIRY = dt.timedelta(days=30)


@final
class TokenCreate(
    ObtainTokensSyncController[
        MsgspecSerializer,
        ObtainTokensPayload,
        ObtainTokensResponse,
    ],
):
    """POST /token — issue an access/refresh token pair."""

    auth = None  # this endpoint mints tokens; cannot itself require one
    jwt_expiration = _ACCESS_EXPIRY
    jwt_refresh_expiration = _REFRESH_EXPIRY
    # Declare the 401 ErrorResponse shape so dmr's response validator
    # accepts our handle_error output.
    responses = (
        ResponseSpec(
            return_type=ErrorResponse,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    # Re-decorate `post` so the OpenAPI schema groups this endpoint under
    # the `auth` tag. dmr's parent `post` only sets `status_code=200` and
    # would otherwise leave the operation untagged (Swagger's "default").
    @modify(tags=['auth'], status_code=HTTPStatus.OK)
    def post(
        self,
        parsed_body: Body[ObtainTokensPayload],
    ) -> ObtainTokensResponse:
        """Issue tokens (delegates to the inherited login flow)."""
        log.debug('[FIX] token_create_post tags=auth')
        return self.login(parsed_body)

    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        """Pass-through: payload shape already matches authenticate() kwargs."""
        log.debug('token_create_convert_payload')
        return payload

    @override
    def make_api_response(self) -> ObtainTokensResponse:
        """Issue the access + refresh JWT pair and return the response."""
        log.debug(
            'token_create_make_response',
            user_id=str(self.request.user.pk),
        )
        now = dt.datetime.now(dt.UTC)
        access_token = self.create_jwt_token(token_type='access')  # noqa: S106
        refresh_token = self.create_jwt_token(
            token_type='refresh',  # noqa: S106
            expiration=now + self.jwt_refresh_expiration,
        )
        return ObtainTokensResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: Controller[MsgspecSerializer],
        exc: Exception,
    ) -> HttpResponse:
        """Translate NotAuthenticatedError into our ErrorResponse shape."""
        if isinstance(exc, NotAuthenticatedError):
            log.debug('token_create_invalid_credentials')
            return controller.to_error(
                ErrorResponse(
                    error='INVALID_CREDENTIALS',
                    message='Invalid username or password',
                ),
                status_code=HTTPStatus.UNAUTHORIZED,
            )
        raise exc  # pragma: no cover


@final
class TokenRefresh(
    RefreshTokenSyncController[
        MsgspecSerializer,
        RefreshTokenPayload,
        ObtainTokensResponse,
    ],
):
    """POST /token/refresh — exchange a refresh JWT for a new pair."""

    auth = None  # refresh endpoint authenticates via the refresh token
    jwt_expiration = _ACCESS_EXPIRY
    jwt_refresh_expiration = _REFRESH_EXPIRY
    responses = (
        ResponseSpec(
            return_type=ErrorResponse,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    # See TokenCreate.post — re-decorate so this endpoint is tagged `auth`
    # in the generated OpenAPI document.
    @modify(tags=['auth'], status_code=HTTPStatus.OK)
    def post(
        self,
        parsed_body: Body[RefreshTokenPayload],
    ) -> ObtainTokensResponse:
        """Refresh tokens (delegates to the inherited refresh flow)."""
        log.debug('[FIX] token_refresh_post tags=auth')
        return self.refresh(parsed_body)

    @override
    def convert_refresh_payload(
        self,
        payload: RefreshTokenPayload,
    ) -> str:
        """Extract the refresh token string from the parsed body."""
        log.debug('token_refresh_convert_payload')
        return payload['refresh_token']

    @override
    def make_api_response(self) -> ObtainTokensResponse:
        """Mint a new access + refresh JWT pair."""
        log.debug(
            'token_refresh_make_response',
            user_id=str(self.request.user.pk),
        )
        now = dt.datetime.now(dt.UTC)
        access_token = self.create_jwt_token(token_type='access')  # noqa: S106
        refresh_token = self.create_jwt_token(
            token_type='refresh',  # noqa: S106
            expiration=now + self.jwt_refresh_expiration,
        )
        return ObtainTokensResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: Controller[MsgspecSerializer],
        exc: Exception,
    ) -> HttpResponse:
        """Translate refresh failures into our ErrorResponse shape."""
        if isinstance(exc, NotAuthenticatedError):
            log.debug('token_refresh_invalid')
            return controller.to_error(
                ErrorResponse(
                    error='INVALID_REFRESH_TOKEN',
                    message='Refresh token is invalid or has expired',
                ),
                status_code=HTTPStatus.UNAUTHORIZED,
            )
        raise exc  # pragma: no cover


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
