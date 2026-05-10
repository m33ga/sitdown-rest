import datetime

import attrs
import structlog
from django.conf import settings
from django.utils import timezone
from dmr.security.jwt.token import JWToken

from server.apps.users.infra.repository import RefreshTokenRepository, UserRepository
from server.apps.users.logic.constants import ACCESS_TOKEN_EXPIRY_SECONDS, JWT_ALGORITHM, REFRESH_TOKEN_EXPIRY_DAYS
from server.apps.users.logic.exceptions import AuthenticationError
from server.apps.users.logic.value_objects import TokenCreatePayload, TokenResponse

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class CreateTokensUseCase:
    _user_repo: UserRepository
    _refresh_token_repo: RefreshTokenRepository

    def __call__(self, payload: TokenCreatePayload) -> TokenResponse:
        log.debug('create_tokens_called', username=payload.username)

        user = self._user_repo.authenticate(payload.username, payload.password)
        if user is None:
            log.debug('create_tokens_auth_failed')
            raise AuthenticationError

        now = timezone.now()
        token = JWToken(
            sub=str(user.id),
            exp=now + datetime.timedelta(seconds=ACCESS_TOKEN_EXPIRY_SECONDS),
            extras={'email': user.email, 'role': user.role},
        )
        access_jwt = token.encode(secret=settings.SECRET_KEY, algorithm=JWT_ALGORITHM)

        rt = self._refresh_token_repo.create(
            user=user,
            expires_at=now + datetime.timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
        )

        log.debug('create_tokens_success', user_id=str(user.id))
        return TokenResponse(access_token=access_jwt, refresh_token=str(rt.id))
