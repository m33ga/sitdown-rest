"""Integration tests for ``PATCH /api/v1/meetings/{id}/entries/{user_id}/``."""

from __future__ import annotations

import datetime as dt
import json
import uuid

import pytest
from django.test import Client

from server.apps.groups.models import Group
from server.apps.meetings.models import Meeting, MemberEntry
from server.apps.users.models import User

from ._helpers import auth_headers, make_user


def _patch(
    client: Client,
    meeting_id: uuid.UUID,
    target_user_id: uuid.UUID,
    payload: dict,
    *,
    user: User,
) -> object:
    return client.patch(
        f'/api/v1/meetings/{meeting_id}/entries/{target_user_id}/',
        json.dumps(payload),
        content_type='application/json',
        **auth_headers(user),
    )


@pytest.mark.django_db
def test_entries_update_requires_auth() -> None:
    """PATCH without Bearer returns 401."""
    meeting_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    target_user_id = uuid.UUID('00000000-0000-0000-0000-000000000002')
    response = Client().patch(
        f'/api/v1/meetings/{meeting_id}/entries/{target_user_id}/',
        json.dumps({'done': 'x'}),
        content_type='application/json',
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_entries_update_manager_any_entry(manager: User) -> None:
    """MANAGER can edit any member's entry."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    target = make_user('alice', role='MEMBER')
    entry = MemberEntry.objects.create(meeting=meeting, user=target)

    response = _patch(
        Client(),
        meeting.id,
        target.id,
        {'done': 'shipped feature X'},
        user=manager,
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['done'] == 'shipped feature X'
    entry.refresh_from_db()
    assert entry.done == 'shipped feature X'


@pytest.mark.django_db
def test_entries_update_member_own_entry(member: User) -> None:
    """MEMBER can edit their own entry."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    MemberEntry.objects.create(meeting=meeting, user=member)

    response = _patch(
        Client(),
        meeting.id,
        member.id,
        {'will_do': 'deploy'},
        user=member,
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['will_do'] == 'deploy'


@pytest.mark.django_db
def test_entries_update_member_other_forbidden(member: User) -> None:
    """MEMBER cannot edit another user's entry."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    other = make_user('alice', role='MEMBER')
    MemberEntry.objects.create(meeting=meeting, user=other)

    response = _patch(
        Client(),
        meeting.id,
        other.id,
        {'done': 'should not work'},
        user=member,
    )

    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'


@pytest.mark.django_db
def test_entries_update_guest_forbidden(guest: User) -> None:
    """GUEST cannot edit any entry, even their own."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    MemberEntry.objects.create(meeting=meeting, user=guest)

    response = _patch(
        Client(),
        meeting.id,
        guest.id,
        {'done': 'should not work'},
        user=guest,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_entries_update_completed_meeting_forbidden(manager: User) -> None:
    """Completed meeting → 403 even for MANAGER (read-only takes precedence)."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
        completed=True,
    )
    target = make_user('alice', role='MEMBER')
    MemberEntry.objects.create(meeting=meeting, user=target)

    response = _patch(
        Client(),
        meeting.id,
        target.id,
        {'done': 'too late'},
        user=manager,
    )

    assert response.status_code == 403
    body = json.loads(response.content)
    assert body['error'] == 'FORBIDDEN'


@pytest.mark.django_db
def test_entries_update_meeting_not_found(manager: User) -> None:
    """Unknown meeting UUID → 404."""
    missing = uuid.UUID('00000000-0000-0000-0000-000000000999')
    target = make_user('alice', role='MEMBER')
    response = _patch(
        Client(),
        missing,
        target.id,
        {'done': 'x'},
        user=manager,
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_entries_update_entry_not_found(manager: User) -> None:
    """Meeting exists but no entry for target_user_id → 404."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    target_user_id = uuid.UUID('00000000-0000-0000-0000-000000000777')

    response = _patch(
        Client(),
        meeting.id,
        target_user_id,
        {'done': 'x'},
        user=manager,
    )

    assert response.status_code == 404
    body = json.loads(response.content)
    assert body['error'] == 'NOT_FOUND'
    assert str(target_user_id) in body['message']
    assert str(meeting.id) in body['message']


@pytest.mark.django_db
def test_entries_update_partial_fields(manager: User) -> None:
    """Only the provided fields are changed; others stay intact."""
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
        promised='before',
        done='before',
        will_do='before',
        discussion='before',
        notes='before',
    )

    response = _patch(
        Client(),
        meeting.id,
        target.id,
        {'done': 'after'},
        user=manager,
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['done'] == 'after'
    assert body['promised'] == 'before'
    assert body['will_do'] == 'before'
    assert body['discussion'] == 'before'
    assert body['notes'] == 'before'


@pytest.mark.django_db
def test_entries_update_empty_body_is_noop(manager: User) -> None:
    """An empty PATCH returns 200 and does NOT bump updated_at."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    target = make_user('alice', role='MEMBER')
    entry = MemberEntry.objects.create(
        meeting=meeting,
        user=target,
        done='unchanged',
    )
    original_updated_at = entry.updated_at

    response = _patch(
        Client(),
        meeting.id,
        target.id,
        {},
        user=manager,
    )

    assert response.status_code == 200
    body = json.loads(response.content)
    assert body['done'] == 'unchanged'
    entry.refresh_from_db()
    assert entry.updated_at == original_updated_at


@pytest.mark.django_db
def test_entries_update_full_body(manager: User) -> None:
    """All five fields can be updated in one PATCH."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    target = make_user('alice', role='MEMBER')
    MemberEntry.objects.create(meeting=meeting, user=target)

    response = _patch(
        Client(),
        meeting.id,
        target.id,
        {
            'promised': 'p',
            'done': 'd',
            'will_do': 'w',
            'discussion': 'di',
            'notes': 'n',
        },
        user=manager,
    )

    body = json.loads(response.content)
    assert body['promised'] == 'p'
    assert body['done'] == 'd'
    assert body['will_do'] == 'w'
    assert body['discussion'] == 'di'
    assert body['notes'] == 'n'
