"""Integration tests for ``GET /api/v1/groups/{group_id}/meetings/``."""

from __future__ import annotations

import datetime
import json
import uuid

import pytest
from django.test import Client

from server.apps.groups.models import Group, ProjectMember
from server.apps.meetings.models import Meeting
from server.apps.users.models import User

from ._helpers import auth_headers


def _get(
    client: Client,
    group_id: uuid.UUID,
    *,
    user: User,
    qs: str = '',
) -> object:
    return client.get(
        f'/api/v1/groups/{group_id}/meetings/{qs}',
        **auth_headers(user),
    )


@pytest.mark.django_db
def test_meetings_list_requires_auth() -> None:
    """GET without Bearer returns 401."""
    group_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    response = Client().get(f'/api/v1/groups/{group_id}/meetings/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_meetings_list_manager_sees_all(manager: User) -> None:
    """MANAGER can list meetings of any group."""
    group = Group.objects.create(name='g')
    Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )

    response = _get(Client(), group.id, user=manager)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['total'] == 1
    assert body['results'][0]['title'] == 'm1'


@pytest.mark.django_db
def test_meetings_list_member_with_access(member: User) -> None:
    """MEMBER who is a ProjectMember of the group can list."""
    group = Group.objects.create(name='g')
    ProjectMember.objects.create(group=group, user=member)
    Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )

    response = _get(Client(), group.id, user=member)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['total'] == 1


@pytest.mark.django_db
def test_meetings_list_member_without_access_forbidden(
    member: User,
) -> None:
    """MEMBER who is NOT a ProjectMember of the group gets 403."""
    group = Group.objects.create(name='g')

    response = _get(Client(), group.id, user=member)

    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'


@pytest.mark.django_db
def test_meetings_list_guest_with_access(guest: User) -> None:
    """GUEST who is a ProjectMember of the group can list."""
    group = Group.objects.create(name='g')
    ProjectMember.objects.create(group=group, user=guest)
    Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )

    response = _get(Client(), group.id, user=guest)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['total'] == 1


@pytest.mark.django_db
def test_meetings_list_group_not_found(manager: User) -> None:
    """Unknown group UUID returns 404."""
    missing = uuid.UUID('00000000-0000-0000-0000-000000000999')
    response = _get(Client(), missing, user=manager)
    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'


@pytest.mark.django_db
def test_meetings_list_orders_by_date_desc(manager: User) -> None:
    """Meetings are returned with the most recent date first."""
    group = Group.objects.create(name='g')
    Meeting.objects.create(
        group=group,
        title='oldest',
        date=datetime.date(2026, 1, 1),
    )
    Meeting.objects.create(
        group=group,
        title='middle',
        date=datetime.date(2026, 3, 1),
    )
    Meeting.objects.create(
        group=group,
        title='newest',
        date=datetime.date(2026, 5, 1),
    )

    response = _get(Client(), group.id, user=manager)

    body = json.loads(response.content)
    titles = [r['title'] for r in body['results']]
    assert titles == ['newest', 'middle', 'oldest']


@pytest.mark.django_db
def test_meetings_list_pagination(manager: User) -> None:
    """?page=2&per_page=1 returns the second item."""
    group = Group.objects.create(name='g')
    Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )
    Meeting.objects.create(
        group=group,
        title='m2',
        date=datetime.date(2026, 4, 1),
    )

    response = _get(Client(), group.id, user=manager, qs='?page=2&per_page=1')

    body = json.loads(response.content)
    assert body['total'] == 2
    assert body['page'] == 2
    assert body['per_page'] == 1
    assert len(body['results']) == 1
    assert body['results'][0]['title'] == 'm2'


@pytest.mark.django_db
def test_meetings_list_invalid_pagination_falls_back(manager: User) -> None:
    """Garbage page/per_page values fall back to defaults."""
    group = Group.objects.create(name='g')
    response = _get(
        Client(),
        group.id,
        user=manager,
        qs='?page=abc&per_page=def',
    )
    body = json.loads(response.content)
    assert body['page'] == 1
    assert body['per_page'] == 20


@pytest.mark.django_db
def test_meetings_list_per_page_capped(manager: User) -> None:
    """per_page is capped at 100."""
    group = Group.objects.create(name='g')
    response = _get(Client(), group.id, user=manager, qs='?per_page=999')
    body = json.loads(response.content)
    assert body['per_page'] == 100


@pytest.mark.django_db
def test_meetings_list_empty(manager: User) -> None:
    """Empty meetings list returns total=0 with empty results."""
    group = Group.objects.create(name='g')
    response = _get(Client(), group.id, user=manager)
    body = json.loads(response.content)
    assert body['total'] == 0
    assert body['results'] == []
