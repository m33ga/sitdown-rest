"""Helper functions for users API tests."""

from __future__ import annotations

import datetime

from django.conf import settings
from django.utils import timezone
from dmr.security.jwt.token import JWToken

from server.apps.users.logic.constants import (
    ACCESS_TOKEN_EXPIRY_SECONDS,
    JWT_ALGORITHM,
)
from server.apps.users.models import User


def make_user(
    username: str,
    *,
    role: str = 'MEMBER',
    password: str = 'pw-secret-123',  # noqa: S107
    first_name: str = '',
    last_name: str = '',
    email: str | None = None,
) -> User:
    """Create a user with a unique email and the given role."""
    user = User.objects.create_user(
        username=username,
        email=email if email is not None else f'{username}@example.com',
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    user.role = role
    user.save(update_fields=['role'])
    return user


def make_token(user: User) -> str:
    """Encode a valid access JWT for ``user`` (parity with TokenCreate)."""
    now = timezone.now()
    token = JWToken(
        sub=str(user.id),
        exp=now + datetime.timedelta(seconds=ACCESS_TOKEN_EXPIRY_SECONDS),
        extras={'type': 'access'},
    )
    return token.encode(secret=settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def auth_headers(user: User) -> dict[str, str]:
    """Return Django test client extra kwargs with a Bearer header."""
    return {'HTTP_AUTHORIZATION': f'Bearer {make_token(user)}'}
