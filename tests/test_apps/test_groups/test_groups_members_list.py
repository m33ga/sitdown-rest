"""Integration tests for ``GET /api/v1/groups/{id}/members/``."""

from __future__ import annotations

import json
import uuid

import pytest
from django.test import Client

from server.apps.groups.models import Group, ProjectMember
from server.apps.users.models import User

from ._helpers import auth_headers, make_user


def _get(
    client: Client,
    group_id: uuid.UUID,
    *,
    user: User,
) -> object:
    return client.get(
        f'/api/v1/groups/{group_id}/members/',
        **auth_headers(user),
    )


@pytest.mark.django_db
def test_members_list_requires_auth() -> None:
    """GET without Bearer returns 401."""
    group_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    response = Client().get(f'/api/v1/groups/{group_id}/members/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_members_list_manager_sees_all(manager: User) -> None:
    """MANAGER can list members of any group."""
    group = Group.objects.create(name='g')
    member = make_user('alice', role='MEMBER')
    ProjectMember.objects.create(group=group, user=member)

    response = _get(Client(), group.id, user=manager)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert len(body) == 1
    assert body[0]['email'] == 'alice@example.com'


@pytest.mark.django_db
def test_members_list_member_with_access(member: User) -> None:
    """MEMBER who is a ProjectMember of the group can list."""
    group = Group.objects.create(name='g')
    ProjectMember.objects.create(group=group, user=member)

    response = _get(Client(), group.id, user=member)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert len(body) == 1
    assert body[0]['email'] == 'member@example.com'


@pytest.mark.django_db
def test_members_list_member_without_access_forbidden(member: User) -> None:
    """MEMBER who is NOT a ProjectMember gets 403."""
    group = Group.objects.create(name='g')

    response = _get(Client(), group.id, user=member)

    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'


@pytest.mark.django_db
def test_members_list_guest_with_access(guest: User) -> None:
    """GUEST who is a ProjectMember of the group can list."""
    group = Group.objects.create(name='g')
    ProjectMember.objects.create(group=group, user=guest)

    response = _get(Client(), group.id, user=guest)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert len(body) == 1


@pytest.mark.django_db
def test_members_list_group_not_found(manager: User) -> None:
    """Unknown UUID returns 404."""
    missing_id = uuid.UUID('00000000-0000-0000-0000-000000000999')
    response = _get(Client(), missing_id, user=manager)
    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'


@pytest.mark.django_db
def test_members_list_returns_user_id_not_member_id(manager: User) -> None:
    """Payload `id` field equals the user's UUID, not membership row id."""
    group = Group.objects.create(name='g')
    member_user = make_user('alice', role='MEMBER')
    membership = ProjectMember.objects.create(
        group=group,
        user=member_user,
    )

    response = _get(Client(), group.id, user=manager)

    body = json.loads(response.content)
    assert body[0]['id'] == str(member_user.id)
    assert body[0]['id'] != str(membership.id)


@pytest.mark.django_db
def test_members_list_includes_role(manager: User) -> None:
    """Payload reflects each member's User.role."""
    group = Group.objects.create(name='g')
    ProjectMember.objects.create(
        group=group,
        user=make_user('mem', role='MEMBER'),
    )
    ProjectMember.objects.create(
        group=group,
        user=make_user('gst', role='GUEST'),
    )

    response = _get(Client(), group.id, user=manager)

    body = json.loads(response.content)
    roles = sorted(record['role'] for record in body)
    assert roles == ['GUEST', 'MEMBER']
