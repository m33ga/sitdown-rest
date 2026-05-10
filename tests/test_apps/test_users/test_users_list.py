"""Integration tests for ``GET /api/v1/users/``."""

from __future__ import annotations

import json

import pytest
from django.test import Client

from server.apps.users.models import User

from ._helpers import auth_headers, make_user


@pytest.mark.django_db
def test_users_list_requires_auth() -> None:
    """Unauthenticated requests receive 401."""
    response = Client().get('/api/v1/users/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_users_list_member_forbidden(member: User) -> None:
    """MEMBER receives 403 with the FORBIDDEN error code."""
    response = Client().get('/api/v1/users/', **auth_headers(member))

    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'


@pytest.mark.django_db
def test_users_list_guest_forbidden(guest: User) -> None:
    """GUEST receives 403 with the FORBIDDEN error code."""
    response = Client().get('/api/v1/users/', **auth_headers(guest))

    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'


@pytest.mark.django_db
def test_users_list_manager_returns_directory(manager: User) -> None:
    """MANAGER receives a paginated directory ordered by username."""
    make_user('alice', role='MEMBER', first_name='Alice', last_name='Smith')
    make_user('bob', role='GUEST', first_name='Bob')

    response = Client().get('/api/v1/users/', **auth_headers(manager))

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['total'] == 3
    assert body['page'] == 1
    assert body['per_page'] == 20
    usernames = [u['name'] for u in body['results']]
    # Names map to: alice -> 'Alice Smith', bob -> 'Bob', manager -> 'manager'.
    # Ordering is by username ascending: alice, bob, manager.
    assert usernames == ['Alice Smith', 'Bob', 'manager']
    assert body['results'][0]['email'] == 'alice@example.com'
    assert body['results'][0]['role'] == 'MEMBER'


@pytest.mark.django_db
def test_users_list_search_email(manager: User) -> None:
    """Search filters by email substring (case-insensitive)."""
    make_user('alice', email='alice@company.com')
    make_user('bob', email='bob@other.org')

    response = Client().get(
        '/api/v1/users/?search=COMPANY',
        **auth_headers(manager),
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['total'] == 1
    assert body['results'][0]['email'] == 'alice@company.com'


@pytest.mark.django_db
def test_users_list_search_first_name(manager: User) -> None:
    """Search filters by first_name substring."""
    make_user('a', first_name='Alice')
    make_user('b', first_name='Bob')

    response = Client().get(
        '/api/v1/users/?search=ali',
        **auth_headers(manager),
    )

    body = json.loads(response.content)
    assert body['total'] == 1
    assert body['results'][0]['name'] == 'Alice'


@pytest.mark.django_db
def test_users_list_search_last_name(manager: User) -> None:
    """Search filters by last_name substring."""
    make_user('a', first_name='Alice', last_name='Smith')
    make_user('b', first_name='Bob', last_name='Brown')

    response = Client().get(
        '/api/v1/users/?search=smi',
        **auth_headers(manager),
    )

    body = json.loads(response.content)
    assert body['total'] == 1
    assert body['results'][0]['name'] == 'Alice Smith'


@pytest.mark.django_db
def test_users_list_pagination(manager: User) -> None:
    """``per_page`` and ``page`` slice results correctly."""
    for index in range(25):
        make_user(f'user{index:02d}', role='MEMBER')

    response = Client().get(
        '/api/v1/users/?per_page=10&page=2',
        **auth_headers(manager),
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['total'] == 26  # 25 seeded + the manager
    assert body['page'] == 2
    assert body['per_page'] == 10
    assert len(body['results']) == 10


@pytest.mark.django_db
def test_users_list_out_of_range_page(manager: User) -> None:
    """A page past the last row returns empty results with the right total."""
    response = Client().get(
        '/api/v1/users/?page=999',
        **auth_headers(manager),
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['total'] == 1
    assert body['results'] == []


@pytest.mark.django_db
def test_users_list_per_page_clamped_to_max(manager: User) -> None:
    """``per_page`` greater than 100 is clamped to 100."""
    response = Client().get(
        '/api/v1/users/?per_page=500',
        **auth_headers(manager),
    )

    body = json.loads(response.content)
    assert body['per_page'] == 100


@pytest.mark.django_db
def test_users_list_per_page_zero_clamped_to_minimum(
    manager: User,
) -> None:
    """``per_page=0`` is clamped to the minimum of 1."""
    response = Client().get(
        '/api/v1/users/?per_page=0',
        **auth_headers(manager),
    )

    body = json.loads(response.content)
    assert body['per_page'] == 1


@pytest.mark.django_db
def test_users_list_bogus_pagination_falls_back_to_defaults(
    manager: User,
) -> None:
    """Non-integer pagination params fall back to defaults (no 400)."""
    response = Client().get(
        '/api/v1/users/?page=abc&per_page=xyz',
        **auth_headers(manager),
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['page'] == 1
    assert body['per_page'] == 20


@pytest.mark.django_db
def test_users_list_empty_search_treated_as_no_filter(
    manager: User,
) -> None:
    """An empty/whitespace ``search`` query param does not filter."""
    make_user('alice', role='MEMBER')

    response = Client().get(
        '/api/v1/users/?search=   ',
        **auth_headers(manager),
    )

    body = json.loads(response.content)
    assert body['total'] == 2
