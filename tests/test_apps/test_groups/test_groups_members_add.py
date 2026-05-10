"""Integration tests for ``POST /api/v1/groups/{id}/members/``."""

from __future__ import annotations

import json
import uuid

import pytest
from django.test import Client

from server.apps.groups.models import Group, ProjectMember
from server.apps.users.models import User

from ._helpers import auth_headers, make_user


def _post(
    client: Client,
    group_id: uuid.UUID,
    payload: dict,
    *,
    user: User,
) -> object:
    return client.post(
        f'/api/v1/groups/{group_id}/members/',
        json.dumps(payload),
        content_type='application/json',
        **auth_headers(user),
    )


@pytest.mark.django_db
def test_members_add_requires_auth() -> None:
    """POST without Bearer returns 401."""
    group_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    user_id = uuid.UUID('00000000-0000-0000-0000-000000000002')
    response = Client().post(
        f'/api/v1/groups/{group_id}/members/',
        json.dumps({'user_id': str(user_id)}),
        content_type='application/json',
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_members_add_manager_success(manager: User) -> None:
    """MANAGER POST returns 201 with the new member's payload."""
    group = Group.objects.create(name='g')
    target = make_user('alice', role='MEMBER')

    response = _post(
        Client(),
        group.id,
        {'user_id': str(target.id)},
        user=manager,
    )

    assert response.status_code == 201
    body = json.loads(response.content)
    assert body['id'] == str(target.id)
    assert body['email'] == 'alice@example.com'
    assert body['role'] == 'MEMBER'
    assert ProjectMember.objects.filter(
        group=group,
        user=target,
    ).exists()


@pytest.mark.django_db
def test_members_add_member_forbidden(member: User) -> None:
    """Non-MANAGER POST returns 403."""
    group = Group.objects.create(name='g')
    target = make_user('alice', role='MEMBER')

    response = _post(
        Client(),
        group.id,
        {'user_id': str(target.id)},
        user=member,
    )

    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'
    assert not ProjectMember.objects.filter(group=group).exists()


@pytest.mark.django_db
def test_members_add_guest_forbidden(guest: User) -> None:
    """GUEST POST returns 403."""
    group = Group.objects.create(name='g')
    target = make_user('alice', role='MEMBER')

    response = _post(
        Client(),
        group.id,
        {'user_id': str(target.id)},
        user=guest,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_members_add_group_not_found(manager: User) -> None:
    """Unknown group UUID returns 404."""
    missing_id = uuid.UUID('00000000-0000-0000-0000-000000000123')
    target = make_user('alice', role='MEMBER')

    response = _post(
        Client(),
        missing_id,
        {'user_id': str(target.id)},
        user=manager,
    )

    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'


@pytest.mark.django_db
def test_members_add_user_not_found(manager: User) -> None:
    """Unknown user_id returns 404."""
    group = Group.objects.create(name='g')
    unknown_user_id = uuid.UUID('00000000-0000-0000-0000-000000000777')

    response = _post(
        Client(),
        group.id,
        {'user_id': str(unknown_user_id)},
        user=manager,
    )

    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'
    assert str(unknown_user_id) in body['message']


@pytest.mark.django_db
def test_members_add_duplicate_returns_409(manager: User) -> None:
    """Adding the same user twice returns 409 CONFLICT."""
    group = Group.objects.create(name='g')
    target = make_user('alice', role='MEMBER')
    ProjectMember.objects.create(group=group, user=target)

    response = _post(
        Client(),
        group.id,
        {'user_id': str(target.id)},
        user=manager,
    )

    assert response.status_code == 409
    body = json.loads(response.content)
    assert body['error'] == 'CONFLICT'


@pytest.mark.django_db
def test_members_add_manager_role_user_allowed(manager: User) -> None:
    """Adding a MANAGER-role user is allowed (deviates from openapi original).

    Pin for the project decision: MANAGER members are allowed in the
    ProjectMember table for parity with MEMBER/GUEST.
    """
    group = Group.objects.create(name='g')
    other_manager = make_user('boss', role='MANAGER')

    response = _post(
        Client(),
        group.id,
        {'user_id': str(other_manager.id)},
        user=manager,
    )

    assert response.status_code == 201
    body = json.loads(response.content)
    assert body['role'] == 'MANAGER'
