"""Integration tests for ``POST /api/v1/groups/{group_id}/meetings/``."""

from __future__ import annotations

import datetime
import json
import uuid

import pytest
from django.test import Client

from server.apps.groups.models import Group, ProjectMember
from server.apps.meetings.models import Meeting, MemberEntry
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
        f'/api/v1/groups/{group_id}/meetings/',
        json.dumps(payload),
        content_type='application/json',
        **auth_headers(user),
    )


@pytest.mark.django_db
def test_meetings_create_requires_auth() -> None:
    """POST without Bearer returns 401."""
    group_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    response = Client().post(
        f'/api/v1/groups/{group_id}/meetings/',
        json.dumps({'date': '2026-05-01'}),
        content_type='application/json',
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_meetings_create_manager_success(manager: User) -> None:
    """MANAGER POST returns 201 with the meeting payload."""
    group = Group.objects.create(name='g')
    response = _post(
        Client(),
        group.id,
        {'date': '2026-05-01', 'title': 'standup · 2026-05-01'},
        user=manager,
    )

    assert response.status_code == 201
    body = json.loads(response.content)
    assert body['title'] == 'standup · 2026-05-01'
    assert body['date'] == '2026-05-01'
    assert body['completed'] is False
    assert Meeting.objects.filter(group=group).count() == 1


@pytest.mark.django_db
def test_meetings_create_member_forbidden(member: User) -> None:
    """Non-MANAGER POST returns 403."""
    group = Group.objects.create(name='g')
    response = _post(
        Client(),
        group.id,
        {'date': '2026-05-01'},
        user=member,
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_meetings_create_guest_forbidden(guest: User) -> None:
    """GUEST POST returns 403."""
    group = Group.objects.create(name='g')
    response = _post(
        Client(),
        group.id,
        {'date': '2026-05-01'},
        user=guest,
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_meetings_create_group_not_found(manager: User) -> None:
    """Unknown group UUID returns 404."""
    missing = uuid.UUID('00000000-0000-0000-0000-000000000888')
    response = _post(
        Client(),
        missing,
        {'date': '2026-05-01'},
        user=manager,
    )
    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'


@pytest.mark.django_db
def test_meetings_create_duplicate_returns_409(manager: User) -> None:
    """Creating two meetings with the same (group, date) returns 409."""
    group = Group.objects.create(name='g')
    Meeting.objects.create(
        group=group,
        title='first',
        date=datetime.date(2026, 5, 1),
    )

    response = _post(
        Client(),
        group.id,
        {'date': '2026-05-01'},
        user=manager,
    )

    assert response.status_code == 409
    body = json.loads(response.content)
    assert body['error'] == 'CONFLICT'


@pytest.mark.django_db
def test_meetings_create_title_default(manager: User) -> None:
    """Omitting title falls back to ``standup · {date}``."""
    group = Group.objects.create(name='g')
    response = _post(
        Client(),
        group.id,
        {'date': '2026-05-01'},
        user=manager,
    )
    body = json.loads(response.content)
    assert body['title'] == 'standup · 2026-05-01'


@pytest.mark.django_db
def test_meetings_create_blank_title_defaults(manager: User) -> None:
    """Whitespace-only title falls back to the generated default."""
    group = Group.objects.create(name='g')
    response = _post(
        Client(),
        group.id,
        {'date': '2026-05-01', 'title': '   '},
        user=manager,
    )
    body = json.loads(response.content)
    assert body['title'] == 'standup · 2026-05-01'


@pytest.mark.django_db
def test_meetings_create_provided_title_preserved(manager: User) -> None:
    """A non-empty title is kept verbatim (with leading/trailing trim)."""
    group = Group.objects.create(name='g')
    response = _post(
        Client(),
        group.id,
        {'date': '2026-05-01', 'title': '  weekly retro '},
        user=manager,
    )
    body = json.loads(response.content)
    assert body['title'] == 'weekly retro'


@pytest.mark.django_db
def test_meetings_create_eager_entries_for_non_guests(manager: User) -> None:
    """One MemberEntry per non-GUEST ProjectMember of the group."""
    group = Group.objects.create(name='g')
    member_user = make_user('alice', role='MEMBER')
    guest_user = make_user('bob', role='GUEST')
    ProjectMember.objects.create(group=group, user=member_user)
    ProjectMember.objects.create(group=group, user=guest_user)

    response = _post(
        Client(),
        group.id,
        {'date': '2026-05-01'},
        user=manager,
    )

    assert response.status_code == 201
    body = json.loads(response.content)
    meeting_id = uuid.UUID(body['id'])
    entries = MemberEntry.objects.filter(meeting_id=meeting_id)
    assert entries.count() == 1
    assert entries.get().user_id == member_user.id


@pytest.mark.django_db
def test_meetings_create_promised_carry_over(manager: User) -> None:
    """`promised` is auto-populated from each user's most recent will_do."""
    group = Group.objects.create(name='g')
    user_a = make_user('alice', role='MEMBER')
    user_b = make_user('bob', role='MEMBER')
    ProjectMember.objects.create(group=group, user=user_a)
    ProjectMember.objects.create(group=group, user=user_b)

    earlier = Meeting.objects.create(
        group=group,
        title='earlier',
        date=datetime.date(2026, 4, 1),
    )
    MemberEntry.objects.create(
        meeting=earlier,
        user=user_a,
        will_do='deploy v1',
    )
    # user_b had only an empty will_do — should NOT carry over.
    MemberEntry.objects.create(
        meeting=earlier,
        user=user_b,
        will_do='',
    )
    later = Meeting.objects.create(
        group=group,
        title='later',
        date=datetime.date(2026, 4, 15),
    )
    MemberEntry.objects.create(
        meeting=later,
        user=user_a,
        will_do='deploy v2',
    )

    response = _post(
        Client(),
        group.id,
        {'date': '2026-05-01'},
        user=manager,
    )

    assert response.status_code == 201
    new_meeting_id = uuid.UUID(json.loads(response.content)['id'])
    entry_a = MemberEntry.objects.get(meeting_id=new_meeting_id, user=user_a)
    entry_b = MemberEntry.objects.get(meeting_id=new_meeting_id, user=user_b)
    assert entry_a.promised == 'deploy v2'  # most-recent non-empty
    assert not entry_b.promised  # no prior non-empty will_do


@pytest.mark.django_db
def test_meetings_create_carry_over_scoped_to_group(manager: User) -> None:
    """Carry-over does not leak from a different group."""
    group_a = Group.objects.create(name='ga')
    group_b = Group.objects.create(name='gb')
    user = make_user('alice', role='MEMBER')
    ProjectMember.objects.create(group=group_a, user=user)
    ProjectMember.objects.create(group=group_b, user=user)

    other_meeting = Meeting.objects.create(
        group=group_b,
        title='other',
        date=datetime.date(2026, 4, 1),
    )
    MemberEntry.objects.create(
        meeting=other_meeting,
        user=user,
        will_do='deploy v1 (other group)',
    )

    response = _post(
        Client(),
        group_a.id,
        {'date': '2026-05-01'},
        user=manager,
    )

    new_meeting_id = uuid.UUID(json.loads(response.content)['id'])
    entry = MemberEntry.objects.get(meeting_id=new_meeting_id, user=user)
    assert not entry.promised
