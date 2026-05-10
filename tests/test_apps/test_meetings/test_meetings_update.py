"""Integration tests for ``PATCH /api/v1/meetings/{id}/``."""

from __future__ import annotations

import datetime
import json
import uuid

import pytest
from django.test import Client

from server.apps.groups.models import Group
from server.apps.meetings.models import Meeting
from server.apps.users.models import User

from ._helpers import auth_headers


def _patch(
    client: Client,
    meeting_id: uuid.UUID,
    payload: dict,
    *,
    user: User,
) -> object:
    return client.patch(
        f'/api/v1/meetings/{meeting_id}/',
        json.dumps(payload),
        content_type='application/json',
        **auth_headers(user),
    )


@pytest.mark.django_db
def test_meetings_update_requires_auth() -> None:
    """PATCH without Bearer returns 401."""
    meeting_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    response = Client().patch(
        f'/api/v1/meetings/{meeting_id}/',
        json.dumps({'completed': True}),
        content_type='application/json',
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_meetings_update_manager_marks_completed(manager: User) -> None:
    """MANAGER can flip `completed` to True."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )

    response = _patch(Client(), meeting.id, {'completed': True}, user=manager)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['completed'] is True
    meeting.refresh_from_db()
    assert meeting.completed is True


@pytest.mark.django_db
def test_meetings_update_manager_renames(manager: User) -> None:
    """MANAGER can change the title."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )

    response = _patch(
        Client(),
        meeting.id,
        {'title': 'standup · 2026-05-01 (retro)'},
        user=manager,
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['title'] == 'standup · 2026-05-01 (retro)'


@pytest.mark.django_db
def test_meetings_update_manager_changes_date(manager: User) -> None:
    """MANAGER can change the meeting date."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )

    response = _patch(
        Client(),
        meeting.id,
        {'date': '2026-05-08'},
        user=manager,
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['date'] == '2026-05-08'


@pytest.mark.django_db
def test_meetings_update_manager_combined(manager: User) -> None:
    """MANAGER can change multiple fields in one PATCH."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )

    response = _patch(
        Client(),
        meeting.id,
        {'title': 'renamed', 'date': '2026-05-15', 'completed': True},
        user=manager,
    )

    body = json.loads(response.content)
    assert body['title'] == 'renamed'
    assert body['date'] == '2026-05-15'
    assert body['completed'] is True


@pytest.mark.django_db
def test_meetings_update_member_forbidden(member: User) -> None:
    """Non-MANAGER PATCH returns 403."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )

    response = _patch(
        Client(),
        meeting.id,
        {'completed': True},
        user=member,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_meetings_update_not_found(manager: User) -> None:
    """Unknown meeting UUID returns 404."""
    missing = uuid.UUID('00000000-0000-0000-0000-000000000777')
    response = _patch(
        Client(),
        missing,
        {'completed': True},
        user=manager,
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_meetings_update_date_collision_returns_409(manager: User) -> None:
    """Date change colliding with another meeting in the group → 409."""
    group = Group.objects.create(name='g')
    Meeting.objects.create(
        group=group,
        title='taken',
        date=datetime.date(2026, 5, 1),
    )
    other = Meeting.objects.create(
        group=group,
        title='other',
        date=datetime.date(2026, 5, 8),
    )

    response = _patch(
        Client(),
        other.id,
        {'date': '2026-05-01'},
        user=manager,
    )

    assert response.status_code == 409
    body = json.loads(response.content)
    assert body['error'] == 'CONFLICT'


@pytest.mark.django_db
def test_meetings_update_empty_body_is_noop(manager: User) -> None:
    """An empty PATCH body returns 200 without changing anything."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
        completed=False,
    )

    response = _patch(Client(), meeting.id, {}, user=manager)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['title'] == 'm1'
    assert body['date'] == '2026-05-01'
    assert body['completed'] is False
