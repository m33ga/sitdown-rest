from __future__ import annotations

import datetime as dt
from http import HTTPStatus
from typing import TYPE_CHECKING, final, override

import structlog
from django.conf import settings
from dmr import Body, Controller, ResponseSpec, modify
from dmr.exceptions import NotAuthenticatedError
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.response import APIError
from dmr.security.jwt.token import JWToken
from dmr.security.jwt.views import (
    ObtainTokensPayload,
    ObtainTokensResponse,
    ObtainTokensSyncController,
    RefreshTokenPayload,
    RefreshTokenSyncController,
)

from server.apps.users.logic.exceptions import PermissionDeniedError
from server.apps.users.logic.usecases.list_users import ListUsersUseCase
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


def _mint_enriched_token(
    controller: ObtainTokensSyncController[
        MsgspecSerializer,
        ObtainTokensPayload,
        ObtainTokensResponse,
    ]
    | RefreshTokenSyncController[
        MsgspecSerializer,
        RefreshTokenPayload,
        ObtainTokensResponse,
    ],
    *,
    token_type: str,
    expiration: dt.datetime,
) -> str:
    """Encode a JWT whose ``extras`` carries identity claims for the SPA.

    dmr's stock ``create_jwt_token`` only embeds ``{'type': token_type}``
    in ``extras``. The SPA reads ``payload.extras.role`` (and friends)
    to drive its permission UI, so we mint the token ourselves with
    role + email + name folded into ``extras``. ``JWToken.encode()``
    serialises the dataclass via ``asdict`` so ``extras`` lands as a
    nested object in the JWT payload (NOT flattened to top-level
    claims).

    Falls back to ``user.username`` for ``name`` when ``get_full_name()``
    returns an empty string — mirrors ``UserMapper.to_payload``.
    """
    user = controller.request.user
    full_name = user.get_full_name() or user.username
    log.debug(
        '[FIX] mint_enriched_token',
        user_id=str(user.pk),
        token_type=token_type,
        role=user.role,
    )
    return JWToken(
        sub=str(user.pk),
        exp=expiration,
        iss=controller.jwt_issuer,
        aud=controller.jwt_audiences,
        jti=controller.make_jwt_id(),
        extras={
            'type': token_type,
            'role': user.role,
            'email': user.email,
            'name': full_name,
        },
    ).encode(
        secret=controller.jwt_secret or settings.SECRET_KEY,
        algorithm=controller.jwt_algorithm,
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
        log.debug('token_create_post')
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
        access_token = _mint_enriched_token(
            self,
            token_type='access',  # noqa: S106
            expiration=now + self.jwt_expiration,
        )
        refresh_token = _mint_enriched_token(
            self,
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
        log.debug('token_refresh_post')
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
        access_token = _mint_enriched_token(
            self,
            token_type='access',  # noqa: S106
            expiration=now + self.jwt_expiration,
        )
        refresh_token = _mint_enriched_token(
            self,
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

    @modify(
        status_code=HTTPStatus.OK,
        tags=['users'],
        extra_responses=[
            ResponseSpec(
                return_type=ErrorResponse,
                status_code=HTTPStatus.FORBIDDEN,
            ),
        ],
    )
    def get(self) -> PaginatedUsersPayload:
        """Return a paginated, searchable list of org users."""
        search_raw = self.request.GET.get('search') or ''
        search = search_raw.strip() or None
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
        log.debug(
            'users_list_called',
            search=search,
            page=page,
            per_page=per_page,
        )
        use_case = self.resolve(ListUsersUseCase)
        try:
            result = use_case(
                user=self.request.user,
                search=search,
                page=page,
                per_page=per_page,
            )
        except PermissionDeniedError:
            log.debug('users_list_forbidden')
            raise _forbidden() from None
        log.debug('users_list_done', total=result.total)
        return result
