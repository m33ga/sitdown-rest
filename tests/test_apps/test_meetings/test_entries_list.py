"""Integration tests for ``GET /api/v1/meetings/{id}/entries/``."""

from __future__ import annotations

import datetime as dt
import json
import uuid

import pytest
from django.test import Client
from django.utils import timezone

from server.apps.groups.models import Group, ProjectMember
from server.apps.meetings.models import Meeting, MemberEntry
from server.apps.users.models import User

from ._helpers import auth_headers, make_user


def _get(
    client: Client,
    meeting_id: uuid.UUID,
    *,
    user: User,
) -> object:
    return client.get(
        f'/api/v1/meetings/{meeting_id}/entries/',
        **auth_headers(user),
    )


@pytest.mark.django_db
def test_entries_list_requires_auth() -> None:
    """GET without Bearer returns 401."""
    meeting_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    response = Client().get(f'/api/v1/meetings/{meeting_id}/entries/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_entries_list_manager_sees_all(manager: User) -> None:
    """MANAGER can list entries of any meeting."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    target = make_user('alice', role='MEMBER')
    MemberEntry.objects.create(
        meeting=meeting,
        user=target,
        will_do='task',
    )

    response = _get(Client(), meeting.id, user=manager)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert len(body) == 1
    assert body[0]['user_id'] == str(target.id)
    assert body[0]['will_do'] == 'task'


@pytest.mark.django_db
def test_entries_list_member_with_access(member: User) -> None:
    """MEMBER with ProjectMember row for the parent group can list."""
    group = Group.objects.create(name='g')
    ProjectMember.objects.create(group=group, user=member)
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    MemberEntry.objects.create(meeting=meeting, user=member)

    response = _get(Client(), meeting.id, user=member)

    assert response.status_code == 200
    body = json.loads(response.content)
    assert len(body) == 1


@pytest.mark.django_db
def test_entries_list_member_without_access_forbidden(
    member: User,
) -> None:
    """MEMBER without project membership for the parent group → 403."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )

    response = _get(Client(), meeting.id, user=member)

    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'


@pytest.mark.django_db
def test_entries_list_guest_with_access(guest: User) -> None:
    """GUEST with ProjectMember row can list (read-only access)."""
    group = Group.objects.create(name='g')
    ProjectMember.objects.create(group=group, user=guest)
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )

    response = _get(Client(), meeting.id, user=guest)

    assert response.status_code == 200


@pytest.mark.django_db
def test_entries_list_meeting_not_found(manager: User) -> None:
    """Unknown meeting UUID → 404."""
    missing = uuid.UUID('00000000-0000-0000-0000-000000000999')
    response = _get(Client(), missing, user=manager)
    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'


@pytest.mark.django_db
def test_entries_list_orders_by_updated_at_desc(manager: User) -> None:
    """Most recently edited entry comes first."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    user_a = make_user('alice', role='MEMBER')
    user_b = make_user('bob', role='MEMBER')
    older = MemberEntry.objects.create(meeting=meeting, user=user_a)
    newer = MemberEntry.objects.create(meeting=meeting, user=user_b)
    # Force the timestamps so the assertion is unambiguous regardless
    # of how fast Django creates the rows.
    MemberEntry.objects.filter(pk=older.pk).update(
        updated_at=timezone.now() - dt.timedelta(hours=1),
    )
    MemberEntry.objects.filter(pk=newer.pk).update(
        updated_at=timezone.now(),
    )

    response = _get(Client(), meeting.id, user=manager)

    body = json.loads(response.content)
    user_ids = [r['user_id'] for r in body]
    assert user_ids == [str(user_b.id), str(user_a.id)]


@pytest.mark.django_db
def test_entries_list_excludes_guest_users_from_create_flow(
    manager: User,
) -> None:
    """A meeting POSTed via the API has no entries for GUEST members.

    This pins the upstream Meetings POST flow's GUEST-exclusion rule;
    the GET /entries view simply returns whatever rows exist.
    """
    group = Group.objects.create(name='g')
    member_user = make_user('alice', role='MEMBER')
    guest_user = make_user('bob', role='GUEST')
    ProjectMember.objects.create(group=group, user=member_user)
    ProjectMember.objects.create(group=group, user=guest_user)
    create_response = Client().post(
        f'/api/v1/groups/{group.id}/meetings/',
        json.dumps({'date': '2026-05-01'}),
        content_type='application/json',
        **auth_headers(manager),
    )
    meeting_id = uuid.UUID(json.loads(create_response.content)['id'])

    response = _get(Client(), meeting_id, user=manager)

    body = json.loads(response.content)
    user_ids = {row['user_id'] for row in body}
    assert user_ids == {str(member_user.id)}
