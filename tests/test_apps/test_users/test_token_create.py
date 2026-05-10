"""Integration tests for POST /api/v1/token/."""

import json

import jwt
import pytest
from django.conf import settings
from django.test import Client

from server.apps.users.models import User

TOKEN_URL = '/api/v1/token/'  # noqa: S105


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


def _post(client: Client, payload: dict) -> object:
    return client.post(
        TOKEN_URL,
        json.dumps(payload),
        content_type='application/json',
    )


@pytest.mark.django_db
def test_token_create_success() -> None:
    """Valid credentials return 200 with access_token and refresh_token."""
    _make_user('alice', 'correcthorsebatterystaple')
    client = Client()
    response = _post(
        client,
        {'username': 'alice', 'password': 'correcthorsebatterystaple'},
    )
    assert response.status_code == 200
    data = json.loads(response.content)
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert data['access_token']
    assert data['refresh_token']


@pytest.mark.django_db
def test_token_create_wrong_password() -> None:
    """Wrong password returns 401 with INVALID_CREDENTIALS error code."""
    _make_user('bob', 'correctpassword')
    client = Client()
    response = _post(
        client,
        {'username': 'bob', 'password': 'wrongpassword'},
    )
    assert response.status_code == 401
    data = json.loads(response.content)
    assert data['error'] == 'INVALID_CREDENTIALS'
    assert 'message' in data


@pytest.mark.django_db
def test_token_create_unknown_user() -> None:
    """Non-existent username returns 401 with INVALID_CREDENTIALS error code."""
    client = Client()
    response = _post(
        client,
        {'username': 'nobody', 'password': 'anypass'},
    )
    assert response.status_code == 401
    data = json.loads(response.content)
    assert data['error'] == 'INVALID_CREDENTIALS'


@pytest.mark.django_db
def test_token_create_access_token_is_jwt() -> None:
    """The access_token field is a valid HS256 JWT."""
    _make_user('carol', 'secret123')
    client = Client()
    response = _post(
        client,
        {'username': 'carol', 'password': 'secret123'},
    )
    assert response.status_code == 200
    data = json.loads(response.content)
    access_token = data['access_token']
    decoded = jwt.decode(
        access_token,
        settings.SECRET_KEY,
        algorithms=['HS256'],
    )
    assert 'sub' in decoded
    assert 'exp' in decoded


@pytest.mark.django_db
def test_token_create_access_and_refresh_have_distinct_types() -> None:
    """Access token has `extras.type='access'`; refresh has `'refresh'`."""
    _make_user('dave', 'secret456')
    client = Client()
    response = _post(
        client,
        {'username': 'dave', 'password': 'secret456'},
    )
    assert response.status_code == 200
    data = json.loads(response.content)

    access_decoded = jwt.decode(
        data['access_token'],
        settings.SECRET_KEY,
        algorithms=['HS256'],
    )
    refresh_decoded = jwt.decode(
        data['refresh_token'],
        settings.SECRET_KEY,
        algorithms=['HS256'],
    )

    assert access_decoded['extras']['type'] == 'access'
    assert refresh_decoded['extras']['type'] == 'refresh'
    # Both share the same subject (the authenticated user's pk).
    assert access_decoded['sub'] == refresh_decoded['sub']
