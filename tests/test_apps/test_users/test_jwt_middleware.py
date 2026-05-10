"""Tests for ``server.apps.users.middleware.JWTAuthMiddleware``."""

from __future__ import annotations

import datetime
import json

import pytest
from django.conf import settings
from django.test import Client
from django.utils import timezone
from dmr.security.jwt.token import JWToken

from server.apps.users.logic.constants import JWT_ALGORITHM
from server.apps.users.models import User

GROUPS_URL = '/api/v1/groups/'
TOKEN_URL = '/api/v1/token/'
ADMIN_URL = '/admin/'


def _make_user(username: str, *, role: str = 'MANAGER') -> User:
    user = User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='secret-pw',
    )
    user.role = role
    user.save(update_fields=['role'])
    return user


def _encode_token(
    *,
    sub: str,
    expires_at: datetime.datetime,
    role: str = 'MANAGER',
    email: str = 'x@example.com',
) -> str:
    token = JWToken(
        sub=sub,
        exp=expires_at,
        extras={'email': email, 'role': role},
    )
    return token.encode(
        secret=settings.SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


@pytest.mark.django_db
def test_middleware_skips_token_endpoint() -> None:
    """The /token/ endpoint must not require a Bearer header."""
    client = Client()
    response = client.post(
        TOKEN_URL,
        json.dumps({'username': 'nobody', 'password': 'x'}),
        content_type='application/json',
    )
    assert response.status_code == 401
    assert json.loads(response.content)['error'] == 'INVALID_CREDENTIALS'


@pytest.mark.django_db
def test_middleware_skips_token_refresh_endpoint() -> None:
    """The /token/refresh/ endpoint must not require a Bearer header."""
    client = Client()
    response = client.post(
        '/api/v1/token/refresh/',
        json.dumps({'refresh_token': '00000000-0000-0000-0000-000000000000'}),
        content_type='application/json',
    )
    assert response.status_code == 401
    assert json.loads(response.content)['error'] == 'INVALID_REFRESH_TOKEN'


@pytest.mark.django_db
def test_middleware_requires_bearer_prefix() -> None:
    """A request to a protected endpoint without Authorization header gets 401."""
    client = Client()
    response = client.get(GROUPS_URL)
    assert response.status_code == 401
    body = json.loads(response.content)
    assert body['error'] == 'UNAUTHORIZED'


@pytest.mark.django_db
def test_middleware_rejects_non_bearer_scheme() -> None:
    """A non-Bearer scheme is rejected with 401."""
    client = Client()
    response = client.get(GROUPS_URL, HTTP_AUTHORIZATION='Basic abc')
    assert response.status_code == 401


@pytest.mark.django_db
def test_middleware_rejects_invalid_token() -> None:
    """A garbage JWT returns 401 with INVALID."""
    client = Client()
    response = client.get(GROUPS_URL, HTTP_AUTHORIZATION='Bearer garbage')
    assert response.status_code == 401
    body = json.loads(response.content)
    assert body['error'] == 'UNAUTHORIZED'


@pytest.mark.django_db
def test_middleware_rejects_token_with_non_uuid_sub() -> None:
    """A JWT whose ``sub`` is not a UUID returns 401."""
    expires_at = timezone.now() + datetime.timedelta(seconds=60)
    bad_token = _encode_token(sub='not-a-uuid', expires_at=expires_at)
    client = Client()
    response = client.get(
        GROUPS_URL,
        HTTP_AUTHORIZATION=f'Bearer {bad_token}',
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_middleware_rejects_unknown_user() -> None:
    """A signed JWT with a sub UUID that does not match any user returns 401."""
    expires_at = timezone.now() + datetime.timedelta(seconds=60)
    token_str = _encode_token(
        sub='00000000-0000-0000-0000-000000000999',
        expires_at=expires_at,
    )
    client = Client()
    response = client.get(
        GROUPS_URL,
        HTTP_AUTHORIZATION=f'Bearer {token_str}',
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_middleware_authenticates_valid_user() -> None:
    """A valid JWT for an existing user yields a non-401 downstream response."""
    user = _make_user('alice', role='MANAGER')
    expires_at = timezone.now() + datetime.timedelta(seconds=60)
    token_str = _encode_token(
        sub=str(user.id),
        expires_at=expires_at,
        role='MANAGER',
        email=user.email,
    )
    client = Client()
    response = client.get(
        GROUPS_URL,
        HTTP_AUTHORIZATION=f'Bearer {token_str}',
    )
    assert response.status_code != 401


@pytest.mark.django_db
def test_middleware_does_not_intercept_admin() -> None:
    """Non-API requests bypass the JWT middleware entirely."""
    client = Client()
    response = client.get(ADMIN_URL)
    # The admin login page redirects (302) when unauthenticated.
    assert response.status_code != 401
