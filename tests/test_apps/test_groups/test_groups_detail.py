"""Integration tests for ``PATCH /groups/{id}`` and ``DELETE /groups/{id}``."""

from __future__ import annotations

import json
import uuid

import pytest
from django.test import Client

from server.apps.groups.models import Group
from server.apps.users.models import User

from ._helpers import auth_headers


def _patch(client: Client, group_id: uuid.UUID, payload: dict, *, user: User) -> object:
    return client.patch(
        f'/api/v1/groups/{group_id}/',
        json.dumps(payload),
        content_type='application/json',
        **auth_headers(user),
    )


def _delete(client: Client, group_id: uuid.UUID, *, user: User) -> object:
    return client.delete(
        f'/api/v1/groups/{group_id}/',
        **auth_headers(user),
    )


@pytest.mark.django_db
def test_groups_patch_manager_success(manager: User) -> None:
    """MANAGER PATCH renames the group and returns 200."""
    group = Group.objects.create(name='old')
    response = _patch(Client(), group.id, {'name': 'new'}, user=manager)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['name'] == 'new'
    group.refresh_from_db()
    assert group.name == 'new'


@pytest.mark.django_db
def test_groups_patch_no_change_when_name_omitted(manager: User) -> None:
    """A PATCH with an empty body keeps the existing name."""
    group = Group.objects.create(name='unchanged')
    response = _patch(Client(), group.id, {}, user=manager)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['name'] == 'unchanged'


@pytest.mark.django_db
def test_groups_patch_member_forbidden(member: User) -> None:
    """MEMBER PATCH returns 403."""
    group = Group.objects.create(name='x')
    response = _patch(Client(), group.id, {'name': 'y'}, user=member)
    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'


@pytest.mark.django_db
def test_groups_patch_guest_forbidden(guest: User) -> None:
    """GUEST PATCH returns 403."""
    group = Group.objects.create(name='x')
    response = _patch(Client(), group.id, {'name': 'y'}, user=guest)
    assert response.status_code == 403


@pytest.mark.django_db
def test_groups_patch_not_found(manager: User) -> None:
    """PATCH on a missing UUID returns 404."""
    missing_id = uuid.UUID('00000000-0000-0000-0000-000000000999')
    response = _patch(Client(), missing_id, {'name': 'x'}, user=manager)
    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'


@pytest.mark.django_db
def test_groups_patch_requires_auth() -> None:
    """PATCH without Bearer returns 401."""
    group_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    response = Client().patch(
        f'/api/v1/groups/{group_id}/',
        json.dumps({'name': 'x'}),
        content_type='application/json',
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_groups_delete_manager_success(manager: User) -> None:
    """MANAGER DELETE returns 204 and removes the group."""
    group = Group.objects.create(name='gone')
    response = _delete(Client(), group.id, user=manager)
    assert response.status_code == 204
    assert not Group.objects.filter(pk=group.id).exists()


@pytest.mark.django_db
def test_groups_delete_member_forbidden(member: User) -> None:
    """MEMBER DELETE returns 403 and keeps the group."""
    group = Group.objects.create(name='persist')
    response = _delete(Client(), group.id, user=member)
    assert response.status_code == 403
    assert Group.objects.filter(pk=group.id).exists()


@pytest.mark.django_db
def test_groups_delete_guest_forbidden(guest: User) -> None:
    """GUEST DELETE returns 403."""
    group = Group.objects.create(name='persist')
    response = _delete(Client(), group.id, user=guest)
    assert response.status_code == 403


@pytest.mark.django_db
def test_groups_delete_not_found(manager: User) -> None:
    """DELETE on a missing UUID returns 404."""
    missing_id = uuid.UUID('00000000-0000-0000-0000-000000000123')
    response = _delete(Client(), missing_id, user=manager)
    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'


@pytest.mark.django_db
def test_groups_delete_requires_auth() -> None:
    """DELETE without Bearer returns 401."""
    group_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    response = Client().delete(f'/api/v1/groups/{group_id}/')
    assert response.status_code == 401
