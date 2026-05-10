"""JWT authentication middleware.

Validates Bearer tokens for all API endpoints except the auth endpoints
themselves. On success, sets ``request.user`` to the matching ``User``
instance. On failure, returns a 401 JSON response.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from http import HTTPStatus

import structlog
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from dmr.exceptions import NotAuthenticatedError
from dmr.security.jwt.token import JWToken

from server.apps.users.logic.constants import JWT_ALGORITHM

log = structlog.get_logger()

_API_PREFIX = '/api/v1/'

_SKIP_PATHS = frozenset({
    '/api/v1/token/',
    '/api/v1/token/refresh/',
})

_BEARER_PREFIX = 'Bearer '


class JWTAuthMiddleware:
    """Validate Bearer JWT tokens and attach the current user to the request."""

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> None:
        """Store the downstream view callable."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Authenticate the request, then dispatch downstream."""
        log.debug('jwt_middleware_called', path=request.path)
        if not request.path.startswith(_API_PREFIX):
            return self.get_response(request)
        if request.path in _SKIP_PATHS:
            log.debug('jwt_middleware_skipped', path=request.path)
            return self.get_response(request)

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith(_BEARER_PREFIX):
            log.debug('jwt_middleware_no_bearer')
            return _unauthorized_response()

        token_str = auth_header[len(_BEARER_PREFIX):]
        try:
            token = JWToken.decode(
                token_str,
                secret=settings.SECRET_KEY,
                algorithm=JWT_ALGORITHM,
            )
            user_id = uuid.UUID(token.sub)
        except (NotAuthenticatedError, ValueError):
            log.debug('jwt_middleware_invalid_token')
            return _unauthorized_response('Invalid or expired token')

        from server.apps.users.models import User  # noqa: PLC0415

        user = User.objects.filter(id=user_id).first()
        if user is None:
            log.debug(
                'jwt_middleware_user_not_found',
                user_id=str(user_id),
            )
            return _unauthorized_response('Invalid or expired token')

        log.debug('jwt_middleware_authenticated', user_id=str(user_id))
        request.user = user
        return self.get_response(request)


def _unauthorized_response(
    message: str = 'Authentication credentials were not provided',
) -> HttpResponse:
    body = json.dumps({'error': 'UNAUTHORIZED', 'message': message})
    return HttpResponse(
        body,
        status=HTTPStatus.UNAUTHORIZED,
        content_type='application/json',
    )
