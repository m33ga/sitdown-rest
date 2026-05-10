"""Integration tests for ``GET /api/v1/groups/`` and ``POST /api/v1/groups/``."""

from __future__ import annotations

import json

import pytest
from django.test import Client

from server.apps.groups.models import Group, ProjectMember, UserPinnedGroup
from server.apps.users.models import User
from ._helpers import auth_headers, make_user

GROUPS_URL = '/api/v1/groups/'


def _post(client: Client, payload: dict, *, user: User) -> object:
    return client.post(
        GROUPS_URL,
        json.dumps(payload),
        content_type='application/json',
        **auth_headers(user),
    )


def _get(client: Client, *, user: User, qs: str = '') -> object:
    return client.get(f'{GROUPS_URL}{qs}', **auth_headers(user))


@pytest.mark.django_db
def test_groups_list_requires_auth() -> None:
    """GET /groups without Bearer returns 401."""
    response = Client().get(GROUPS_URL)
    assert response.status_code == 401


@pytest.mark.django_db
def test_groups_list_manager_sees_all(manager: User) -> None:
    """MANAGER sees all groups even without ProjectMember rows."""
    Group.objects.create(name='alpha')
    Group.objects.create(name='beta')
    response = _get(Client(), user=manager)
    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['total'] == 2
    assert {g['name'] for g in body['results']} == {'alpha', 'beta'}


@pytest.mark.django_db
def test_groups_list_member_sees_only_member_groups(member: User) -> None:
    """MEMBER only sees groups with a ProjectMember row for them."""
    visible = Group.objects.create(name='visible')
    Group.objects.create(name='invisible')
    ProjectMember.objects.create(user=member, group=visible)

    response = _get(Client(), user=member)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['total'] == 1
    assert body['results'][0]['name'] == 'visible'


@pytest.mark.django_db
def test_groups_list_guest_sees_only_member_groups(guest: User) -> None:
    """GUEST sees only groups they are project-members of."""
    visible = Group.objects.create(name='visible')
    Group.objects.create(name='invisible')
    ProjectMember.objects.create(user=guest, group=visible)

    response = _get(Client(), user=guest)

    body = json.loads(response.content)
    assert body['total'] == 1
    assert body['results'][0]['name'] == 'visible'


@pytest.mark.django_db
def test_groups_list_pinned_first(manager: User) -> None:
    """Pinned groups must appear before non-pinned, regardless of created_at."""
    older = Group.objects.create(name='older')
    newer = Group.objects.create(name='newer')
    UserPinnedGroup.objects.create(user=manager, group=older)

    response = _get(Client(), user=manager)
    body = json.loads(response.content)

    assert [g['name'] for g in body['results']] == ['older', 'newer']
    assert body['results'][0]['pinned'] is True
    assert body['results'][1]['pinned'] is False


@pytest.mark.django_db
def test_groups_list_search_filters_by_name(manager: User) -> None:
    """?search=foo filters case-insensitively on name."""
    Group.objects.create(name='Project Falcon')
    Group.objects.create(name='Project Eagle')

    response = _get(Client(), user=manager, qs='?search=falcon')

    body = json.loads(response.content)
    assert body['total'] == 1
    assert body['results'][0]['name'] == 'Project Falcon'


@pytest.mark.django_db
def test_groups_list_pagination(manager: User) -> None:
    """?page=2&per_page=1 returns the second item only."""
    Group.objects.create(name='first')
    Group.objects.create(name='second')

    response = _get(Client(), user=manager, qs='?page=2&per_page=1')

    body = json.loads(response.content)
    assert body['total'] == 2
    assert body['page'] == 2
    assert body['per_page'] == 1
    assert len(body['results']) == 1


@pytest.mark.django_db
def test_groups_list_invalid_pagination_falls_back_to_defaults(
    manager: User,
) -> None:
    """Garbage query params fall back to defaults instead of erroring."""
    Group.objects.create(name='alpha')
    response = _get(Client(), user=manager, qs='?page=abc&per_page=def')
    body = json.loads(response.content)
    assert response.status_code == 200
    assert body['page'] == 1
    assert body['per_page'] == 20


@pytest.mark.django_db
def test_groups_list_per_page_capped(manager: User) -> None:
    """per_page is capped at 100."""
    Group.objects.create(name='alpha')
    response = _get(Client(), user=manager, qs='?per_page=999')
    body = json.loads(response.content)
    assert body['per_page'] == 100


@pytest.mark.django_db
def test_groups_create_manager_success(manager: User) -> None:
    """MANAGER POST returns 201 with id, name, created_at."""
    response = _post(Client(), {'name': 'New Group'}, user=manager)

    assert response.status_code == 201
    body = json.loads(response.content)
    assert body['name'] == 'New Group'
    assert 'id' in body
    assert 'created_at' in body
    assert Group.objects.filter(name='New Group').exists()


@pytest.mark.django_db
def test_groups_create_member_forbidden(member: User) -> None:
    """MEMBER POST returns 403 FORBIDDEN."""
    response = _post(Client(), {'name': 'X'}, user=member)
    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'
    assert not Group.objects.filter(name='X').exists()


@pytest.mark.django_db
def test_groups_create_guest_forbidden(guest: User) -> None:
    """GUEST POST returns 403 FORBIDDEN."""
    response = _post(Client(), {'name': 'X'}, user=guest)
    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'


@pytest.mark.django_db
def test_groups_create_requires_auth() -> None:
    """POST /groups without Bearer returns 401."""
    response = Client().post(
        GROUPS_URL,
        json.dumps({'name': 'X'}),
        content_type='application/json',
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_groups_list_self_pin_does_not_show_for_other_user() -> None:
    """``pinned`` is computed per-user."""
    alice = make_user('alice', role='MANAGER')
    bob = make_user('bob', role='MANAGER')
    group = Group.objects.create(name='shared')
    UserPinnedGroup.objects.create(user=alice, group=group)

    alice_resp = _get(Client(), user=alice)
    bob_resp = _get(Client(), user=bob)

    assert json.loads(alice_resp.content)['results'][0]['pinned'] is True
    assert json.loads(bob_resp.content)['results'][0]['pinned'] is False
