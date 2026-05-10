import datetime
from uuid import UUID

import attrs
import structlog
from django.conf import settings
from django.utils import timezone
from dmr.security.jwt.token import JWToken

from server.apps.users.infra.repository import RefreshTokenRepository, UserRepository
from server.apps.users.logic.constants import ACCESS_TOKEN_EXPIRY_SECONDS, JWT_ALGORITHM, REFRESH_TOKEN_EXPIRY_DAYS
from server.apps.users.logic.exceptions import InvalidRefreshTokenError
from server.apps.users.logic.value_objects import TokenRefreshPayload, TokenRefreshResponse

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class RefreshTokensUseCase:
    _user_repo: UserRepository
    _refresh_token_repo: RefreshTokenRepository

    def __call__(self, payload: TokenRefreshPayload) -> TokenRefreshResponse:
        log.debug('refresh_tokens_called')

        try:
            token_id = UUID(payload.refresh_token)
        except ValueError:
            log.debug('refresh_token_invalid', reason='malformed_uuid')
            raise InvalidRefreshTokenError

        rt = self._refresh_token_repo.get_by_id(token_id)
        now = timezone.now()

        if rt is None:
            log.debug('refresh_token_invalid', reason='not_found')
            raise InvalidRefreshTokenError
        if rt.revoked:
            log.debug('refresh_token_invalid', reason='revoked')
            raise InvalidRefreshTokenError
        if rt.expires_at < now:
            log.debug('refresh_token_invalid', reason='expired')
            raise InvalidRefreshTokenError

        self._refresh_token_repo.revoke(rt)

        user = self._user_repo.get_by_id(rt.user_id)

        token = JWToken(
            sub=str(user.id),
            exp=now + datetime.timedelta(seconds=ACCESS_TOKEN_EXPIRY_SECONDS),
            extras={'email': user.email, 'role': user.role},
        )
        access_jwt = token.encode(secret=settings.SECRET_KEY, algorithm=JWT_ALGORITHM)

        new_rt = self._refresh_token_repo.create(
            user=user,
            expires_at=now + datetime.timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
        )

        log.debug('refresh_tokens_success', user_id=str(user.id))
        return TokenRefreshResponse(access_token=access_jwt, refresh_token=str(new_rt.id))
