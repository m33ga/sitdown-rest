import datetime
from uuid import UUID

import attrs
import structlog
from django.contrib.auth import authenticate

from server.apps.users.models import RefreshToken, User

log = structlog.get_logger()


@attrs.define(slots=True)
class UserRepository:
    def authenticate(self, username: str, password: str) -> User | None:
        log.debug('user_authenticate_called', username=username)
        user = authenticate(username=username, password=password)
        if user is None:
            log.debug('user_authentication_failed', username=username)
            return None
        log.debug('user_authenticated', user_id=str(user.id))
        return user  # type: ignore[return-value]

    def get_by_id(self, user_id: UUID) -> User | None:
        log.debug('user_get_by_id_called', user_id=str(user_id))
        try:
            user = User.objects.get(pk=user_id)
            log.debug('user_found', user_id=str(user_id))
            return user
        except User.DoesNotExist:
            log.debug('user_not_found', user_id=str(user_id))
            return None


@attrs.define(slots=True)
class RefreshTokenRepository:
    def create(self, user: User, expires_at: datetime.datetime) -> RefreshToken:
        log.debug('refresh_token_create_called', user_id=str(user.id))
        token = RefreshToken.objects.create(user=user, expires_at=expires_at)
        log.debug('refresh_token_created', token_id=str(token.id))
        return token

    def get_by_id(self, token_id: UUID) -> RefreshToken | None:
        log.debug('refresh_token_get_called', token_id=str(token_id))
        try:
            token = RefreshToken.objects.get(pk=token_id)
            log.debug('refresh_token_found', token_id=str(token_id))
            return token
        except RefreshToken.DoesNotExist:
            log.debug('refresh_token_not_found', token_id=str(token_id))
            return None

    def revoke(self, token: RefreshToken) -> None:
        log.debug('refresh_token_revoke_called', token_id=str(token.id))
        token.revoked = True
        token.save(update_fields=['revoked'])
        log.debug('refresh_token_revoked', token_id=str(token.id))
