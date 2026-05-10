"""Integration tests for POST /api/v1/token/refresh/."""

from __future__ import annotations

import datetime as dt
import json
import uuid

import jwt as pyjwt
import pytest
from django.conf import settings
from django.test import Client
from django.utils import timezone
from dmr.security.jwt.token import JWToken

from server.apps.users.models import User

TOKEN_URL = '/api/v1/token/'  # noqa: S105
REFRESH_URL = '/api/v1/token/refresh/'
JWT_ALGORITHM = 'HS256'


def _make_user(
    username: str,
    password: str,
    *,
    role: str = 'GUEST',
) -> User:
    user = User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password=password,
    )
    user.role = role
    user.save(update_fields=['role'])
    return user


def _create_token_pair(
    client: Client,
    username: str,
    password: str,
) -> dict:
    response = client.post(
        TOKEN_URL,
        json.dumps({'username': username, 'password': password}),
        content_type='application/json',
    )
    assert response.status_code == 200
    return json.loads(response.content)


def _refresh(client: Client, refresh_token: str) -> object:
    return client.post(
        REFRESH_URL,
        json.dumps({'refresh_token': refresh_token}),
        content_type='application/json',
    )


def _encode_token(
    *,
    sub: str,
    expires_at: dt.datetime,
    token_type: str = 'refresh',  # noqa: S107
) -> str:
    """Manually encode a JWT for negative-path tests."""
    return JWToken(
        sub=sub,
        exp=expires_at,
        extras={'type': token_type},
    ).encode(secret=settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


@pytest.mark.django_db
def test_token_refresh_success() -> None:
    """Valid refresh JWT returns 200 with a fresh access/refresh pair."""
    _make_user('refresh_alice', 'pass1')
    client = Client()
    tokens = _create_token_pair(client, 'refresh_alice', 'pass1')

    response = _refresh(client, tokens['refresh_token'])

    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['access_token']
    assert data['refresh_token']
    # The new access token differs from the original (different jti).
    assert data['access_token'] != tokens['access_token']


@pytest.mark.django_db
def test_token_refresh_invalid_token() -> None:
    """Garbage refresh_token string returns 401 with INVALID_REFRESH_TOKEN."""
    client = Client()
    response = _refresh(client, 'not-a-valid-jwt-at-all')
    assert response.status_code == 401
    data = json.loads(response.content)
    assert data['error'] == 'INVALID_REFRESH_TOKEN'


@pytest.mark.django_db
def test_token_refresh_expired_token() -> None:
    """A refresh JWT with `exp` in the past returns 401."""
    user = _make_user('refresh_carol', 'pass3')
    # Manually craft an "expired" refresh token. JWToken's __post_init__
    # rejects past exp values, so we shift `now` forward via leeway tricks
    # — instead, encode at the boundary by passing exp 1 second ahead and
    # then sleeping briefly is unreliable. Use a far-past exp directly via
    # PyJWT to bypass JWToken's constructor validation.

    expired_payload = {
        'sub': str(user.pk),
        'exp': int(
            (timezone.now() - dt.timedelta(days=1)).timestamp(),
        ),
        'iat': int(
            (timezone.now() - dt.timedelta(days=2)).timestamp(),
        ),
        'extras': {'type': 'refresh'},
    }
    expired_token = pyjwt.encode(
        expired_payload,
        settings.SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    client = Client()
    response = _refresh(client, expired_token)
    assert response.status_code == 401
    data = json.loads(response.content)
    assert data['error'] == 'INVALID_REFRESH_TOKEN'


@pytest.mark.django_db
def test_token_refresh_access_token_rejected() -> None:
    """A JWT with `extras.type='access'` cannot be used to refresh."""
    user = _make_user('refresh_dave', 'pass4')
    access_only = _encode_token(
        sub=str(user.pk),
        expires_at=timezone.now() + dt.timedelta(seconds=60),
        token_type='access',
    )

    client = Client()
    response = _refresh(client, access_only)
    assert response.status_code == 401
    data = json.loads(response.content)
    assert data['error'] == 'INVALID_REFRESH_TOKEN'


@pytest.mark.django_db
def test_token_refresh_unknown_user() -> None:
    """A signed refresh JWT whose `sub` doesn't match any user returns 401."""
    unknown_id = uuid.UUID('00000000-0000-0000-0000-000000000999')
    refresh_token = _encode_token(
        sub=str(unknown_id),
        expires_at=timezone.now() + dt.timedelta(days=30),
    )

    client = Client()
    response = _refresh(client, refresh_token)
    assert response.status_code == 401
    data = json.loads(response.content)
    assert data['error'] == 'INVALID_REFRESH_TOKEN'
