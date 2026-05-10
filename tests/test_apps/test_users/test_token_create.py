"""Integration tests for POST /api/v1/token/."""

import json

import jwt
import pytest
from django.conf import settings
from django.test import Client

from server.apps.users.models import User

TOKEN_URL = '/api/v1/token/'


def _make_user(username: str, password: str) -> User:
    return User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password=password,
    )


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
    response = _post(client, {'username': 'alice', 'password': 'correcthorsebatterystaple'})
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
    response = _post(client, {'username': 'bob', 'password': 'wrongpassword'})
    assert response.status_code == 401
    data = json.loads(response.content)
    assert data['error'] == 'INVALID_CREDENTIALS'
    assert 'message' in data


@pytest.mark.django_db
def test_token_create_unknown_user() -> None:
    """Non-existent username returns 401 with INVALID_CREDENTIALS error code."""
    client = Client()
    response = _post(client, {'username': 'nobody', 'password': 'anypass'})
    assert response.status_code == 401
    data = json.loads(response.content)
    assert data['error'] == 'INVALID_CREDENTIALS'


@pytest.mark.django_db
def test_token_create_access_token_is_jwt() -> None:
    """The access_token field is a valid HS256 JWT."""
    _make_user('carol', 'secret123')
    client = Client()
    response = _post(client, {'username': 'carol', 'password': 'secret123'})
    assert response.status_code == 200
    data = json.loads(response.content)
    access_token = data['access_token']
    decoded = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
    assert 'sub' in decoded
    assert 'exp' in decoded


@pytest.mark.django_db
def test_token_create_access_token_contains_role_claim() -> None:
    """The access_token extras contain a role claim."""
    _make_user('dave', 'secret456')
    client = Client()
    response = _post(client, {'username': 'dave', 'password': 'secret456'})
    assert response.status_code == 200
    data = json.loads(response.content)
    access_token = data['access_token']
    decoded = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
    assert 'extras' in decoded
    assert 'role' in decoded['extras']
