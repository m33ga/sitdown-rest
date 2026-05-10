"""Integration tests for POST /api/v1/token/refresh/."""

import datetime
import json
import uuid

import pytest
from django.test import Client
from django.utils import timezone

from server.apps.users.models import RefreshToken, User

TOKEN_URL = '/api/v1/token/'
REFRESH_URL = '/api/v1/token/refresh/'


def _make_user(username: str, password: str) -> User:
    return User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password=password,
    )


def _create_token_pair(client: Client, username: str, password: str) -> dict:
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


@pytest.mark.django_db
def test_token_refresh_success() -> None:
    """Valid refresh token returns 200 with new access_token and refresh_token."""
    _make_user('refresh_alice', 'pass1')
    client = Client()
    tokens = _create_token_pair(client, 'refresh_alice', 'pass1')
    response = _refresh(client, tokens['refresh_token'])
    assert response.status_code == 200
    data = json.loads(response.content)
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert data['access_token']
    assert data['refresh_token']


@pytest.mark.django_db
def test_token_refresh_rotates_token() -> None:
    """Second use of the same refresh token returns 401 (token was revoked on first use)."""
    _make_user('refresh_bob', 'pass2')
    client = Client()
    tokens = _create_token_pair(client, 'refresh_bob', 'pass2')
    old_refresh = tokens['refresh_token']
    first_response = _refresh(client, old_refresh)
    assert first_response.status_code == 200
    second_response = _refresh(client, old_refresh)
    assert second_response.status_code == 401
    data = json.loads(second_response.content)
    assert data['error'] == 'INVALID_REFRESH_TOKEN'


@pytest.mark.django_db
def test_token_refresh_invalid_uuid() -> None:
    """Garbage refresh_token string returns 401 with INVALID_REFRESH_TOKEN."""
    client = Client()
    response = _refresh(client, 'not-a-valid-uuid-at-all')
    assert response.status_code == 401
    data = json.loads(response.content)
    assert data['error'] == 'INVALID_REFRESH_TOKEN'


@pytest.mark.django_db
def test_token_refresh_expired_token() -> None:
    """Expired RefreshToken record returns 401 with INVALID_REFRESH_TOKEN."""
    user = _make_user('refresh_carol', 'pass3')
    expired_token = RefreshToken.objects.create(
        user=user,
        expires_at=timezone.now() - datetime.timedelta(days=1),
    )
    client = Client()
    response = _refresh(client, str(expired_token.id))
    assert response.status_code == 401
    data = json.loads(response.content)
    assert data['error'] == 'INVALID_REFRESH_TOKEN'


@pytest.mark.django_db
def test_token_refresh_revoked_token() -> None:
    """Manually revoked RefreshToken returns 401 with INVALID_REFRESH_TOKEN."""
    user = _make_user('refresh_dave', 'pass4')
    revoked_token = RefreshToken.objects.create(
        user=user,
        expires_at=timezone.now() + datetime.timedelta(days=30),
        revoked=True,
    )
    client = Client()
    response = _refresh(client, str(revoked_token.id))
    assert response.status_code == 401
    data = json.loads(response.content)
    assert data['error'] == 'INVALID_REFRESH_TOKEN'
