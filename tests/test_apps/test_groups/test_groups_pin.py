"""Integration tests for ``PUT/DELETE /groups/{id}/pin``."""

from __future__ import annotations

import json
import uuid

import pytest
from django.test import Client

from server.apps.groups.models import (
    Group,
    ProjectMember,
    UserPinnedGroup,
)
from server.apps.users.models import User

from ._helpers import auth_headers


def _put(client: Client, group_id: uuid.UUID, *, user: User) -> object:
    return client.put(
        f'/api/v1/groups/{group_id}/pin/',
        **auth_headers(user),
    )


def _delete(client: Client, group_id: uuid.UUID, *, user: User) -> object:
    return client.delete(
        f'/api/v1/groups/{group_id}/pin/',
        **auth_headers(user),
    )


@pytest.mark.django_db
def test_groups_pin_manager_success(manager: User) -> None:
    """MANAGER pin returns 204 and persists a UserPinnedGroup row."""
    group = Group.objects.create(name='g')
    response = _put(Client(), group.id, user=manager)
    assert response.status_code == 204
    assert UserPinnedGroup.objects.filter(
        user=manager,
        group=group,
    ).exists()


@pytest.mark.django_db
def test_groups_pin_member_with_access_success(member: User) -> None:
    """MEMBER who is a ProjectMember of the group can pin it."""
    group = Group.objects.create(name='g')
    ProjectMember.objects.create(user=member, group=group)
    response = _put(Client(), group.id, user=member)
    assert response.status_code == 204
    assert UserPinnedGroup.objects.filter(
        user=member,
        group=group,
    ).exists()


@pytest.mark.django_db
def test_groups_pin_idempotent(manager: User) -> None:
    """Pinning an already-pinned group still returns 204."""
    group = Group.objects.create(name='g')
    UserPinnedGroup.objects.create(user=manager, group=group)
    response = _put(Client(), group.id, user=manager)
    assert response.status_code == 204
    assert (
        UserPinnedGroup.objects.filter(
            user=manager,
            group=group,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_groups_pin_not_found(manager: User) -> None:
    """Pinning a missing group returns 404."""
    missing_id = uuid.UUID('00000000-0000-0000-0000-000000000099')
    response = _put(Client(), missing_id, user=manager)
    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'


@pytest.mark.django_db
def test_groups_pin_member_no_access_forbidden(member: User) -> None:
    """MEMBER without ProjectMember row for the group gets 403."""
    group = Group.objects.create(name='g')
    response = _put(Client(), group.id, user=member)
    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'


@pytest.mark.django_db
def test_groups_pin_guest_no_access_forbidden(guest: User) -> None:
    """GUEST without ProjectMember row gets 403."""
    group = Group.objects.create(name='g')
    response = _put(Client(), group.id, user=guest)
    assert response.status_code == 403


@pytest.mark.django_db
def test_groups_pin_requires_auth() -> None:
    """PUT /pin without Bearer returns 401."""
    group_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    response = Client().put(f'/api/v1/groups/{group_id}/pin/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_groups_unpin_success(manager: User) -> None:
    """Unpinning a pinned group returns 204."""
    group = Group.objects.create(name='g')
    UserPinnedGroup.objects.create(user=manager, group=group)
    response = _delete(Client(), group.id, user=manager)
    assert response.status_code == 204
    assert not UserPinnedGroup.objects.filter(
        user=manager,
        group=group,
    ).exists()


@pytest.mark.django_db
def test_groups_unpin_idempotent(manager: User) -> None:
    """Unpinning an unpinned group still returns 204."""
    group = Group.objects.create(name='g')
    response = _delete(Client(), group.id, user=manager)
    assert response.status_code == 204


@pytest.mark.django_db
def test_groups_unpin_not_found(manager: User) -> None:
    """Unpinning a missing group returns 404."""
    missing_id = uuid.UUID('00000000-0000-0000-0000-000000000077')
    response = _delete(Client(), missing_id, user=manager)
    assert response.status_code == 404


@pytest.mark.django_db
def test_groups_unpin_member_no_access_forbidden(member: User) -> None:
    """MEMBER without ProjectMember row cannot unpin (403)."""
    group = Group.objects.create(name='g')
    response = _delete(Client(), group.id, user=member)
    assert response.status_code == 403


@pytest.mark.django_db
def test_groups_unpin_member_with_access_success(member: User) -> None:
    """MEMBER with access can unpin (idempotent)."""
    group = Group.objects.create(name='g')
    ProjectMember.objects.create(user=member, group=group)
    UserPinnedGroup.objects.create(user=member, group=group)
    response = _delete(Client(), group.id, user=member)
    assert response.status_code == 204
    assert not UserPinnedGroup.objects.filter(
        user=member,
        group=group,
    ).exists()


@pytest.mark.django_db
def test_groups_unpin_requires_auth() -> None:
    """DELETE /pin without Bearer returns 401."""
    group_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    response = Client().delete(f'/api/v1/groups/{group_id}/pin/')
    assert response.status_code == 401
