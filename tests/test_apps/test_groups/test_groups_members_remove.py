"""Integration tests for ``DELETE /api/v1/groups/{id}/members/{user_id}/``."""

from __future__ import annotations

import json
import uuid

import pytest
from django.test import Client

from server.apps.groups.models import Group, ProjectMember
from server.apps.users.models import User

from ._helpers import auth_headers, make_user


def _delete(
    client: Client,
    group_id: uuid.UUID,
    target_user_id: uuid.UUID,
    *,
    user: User,
) -> object:
    return client.delete(
        f'/api/v1/groups/{group_id}/members/{target_user_id}/',
        **auth_headers(user),
    )


@pytest.mark.django_db
def test_members_remove_requires_auth() -> None:
    """DELETE without Bearer returns 401."""
    group_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    user_id = uuid.UUID('00000000-0000-0000-0000-000000000002')
    response = Client().delete(
        f'/api/v1/groups/{group_id}/members/{user_id}/',
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_members_remove_manager_success(manager: User) -> None:
    """MANAGER DELETE returns 204 and removes the row."""
    group = Group.objects.create(name='g')
    target = make_user('alice', role='MEMBER')
    ProjectMember.objects.create(group=group, user=target)

    response = _delete(Client(), group.id, target.id, user=manager)

    assert response.status_code == 204
    assert not ProjectMember.objects.filter(
        group=group,
        user=target,
    ).exists()


@pytest.mark.django_db
def test_members_remove_non_manager_forbidden(member: User) -> None:
    """Non-MANAGER DELETE returns 403; row stays."""
    group = Group.objects.create(name='g')
    target = make_user('alice', role='MEMBER')
    ProjectMember.objects.create(group=group, user=target)

    response = _delete(Client(), group.id, target.id, user=member)

    assert response.status_code == 403
    assert ProjectMember.objects.filter(
        group=group,
        user=target,
    ).exists()


@pytest.mark.django_db
def test_members_remove_guest_forbidden(guest: User) -> None:
    """GUEST DELETE returns 403."""
    group = Group.objects.create(name='g')
    target = make_user('alice', role='MEMBER')
    ProjectMember.objects.create(group=group, user=target)

    response = _delete(Client(), group.id, target.id, user=guest)

    assert response.status_code == 403


@pytest.mark.django_db
def test_members_remove_group_not_found(manager: User) -> None:
    """Unknown group UUID returns 404."""
    missing_group = uuid.UUID('00000000-0000-0000-0000-000000000888')
    user_id = uuid.UUID('00000000-0000-0000-0000-000000000007')

    response = _delete(Client(), missing_group, user_id, user=manager)

    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'


@pytest.mark.django_db
def test_members_remove_user_not_a_member(manager: User) -> None:
    """user_id who isn't a member returns 404 NOT_FOUND."""
    group = Group.objects.create(name='g')
    not_a_member = make_user('outsider', role='MEMBER')

    response = _delete(Client(), group.id, not_a_member.id, user=manager)

    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'
    assert 'is not a member' in body['message']


@pytest.mark.django_db
def test_members_remove_preserves_user(manager: User) -> None:
    """Removing membership leaves the User row intact."""
    group = Group.objects.create(name='g')
    target = make_user('alice', role='MEMBER')
    ProjectMember.objects.create(group=group, user=target)

    response = _delete(Client(), group.id, target.id, user=manager)

    assert response.status_code == 204
    assert User.objects.filter(pk=target.pk).exists()
