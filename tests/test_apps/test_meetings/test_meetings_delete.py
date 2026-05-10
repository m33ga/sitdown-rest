"""Integration tests for ``DELETE /api/v1/meetings/{id}/``."""

from __future__ import annotations

import datetime
import uuid

import pytest
from django.test import Client

from server.apps.groups.models import Group
from server.apps.meetings.models import Meeting, MemberEntry
from server.apps.users.models import User

from ._helpers import auth_headers, make_user


def _delete(
    client: Client,
    meeting_id: uuid.UUID,
    *,
    user: User,
) -> object:
    return client.delete(
        f'/api/v1/meetings/{meeting_id}/',
        **auth_headers(user),
    )


@pytest.mark.django_db
def test_meetings_delete_requires_auth() -> None:
    """DELETE without Bearer returns 401."""
    meeting_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
    response = Client().delete(f'/api/v1/meetings/{meeting_id}/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_meetings_delete_manager_success(manager: User) -> None:
    """MANAGER DELETE returns 204; cascades MemberEntry rows."""
    group = Group.objects.create(name='g')
    user = make_user('alice', role='MEMBER')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )
    MemberEntry.objects.create(meeting=meeting, user=user)

    response = _delete(Client(), meeting.id, user=manager)

    assert response.status_code == 204
    assert not Meeting.objects.filter(pk=meeting.id).exists()
    assert not MemberEntry.objects.filter(meeting_id=meeting.id).exists()


@pytest.mark.django_db
def test_meetings_delete_member_forbidden(member: User) -> None:
    """Non-MANAGER DELETE returns 403; meeting stays."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )

    response = _delete(Client(), meeting.id, user=member)

    assert response.status_code == 403
    assert Meeting.objects.filter(pk=meeting.id).exists()


@pytest.mark.django_db
def test_meetings_delete_guest_forbidden(guest: User) -> None:
    """GUEST DELETE returns 403."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )

    response = _delete(Client(), meeting.id, user=guest)

    assert response.status_code == 403


@pytest.mark.django_db
def test_meetings_delete_not_found(manager: User) -> None:
    """Unknown meeting UUID returns 404."""
    missing = uuid.UUID('00000000-0000-0000-0000-000000000666')
    response = _delete(Client(), missing, user=manager)
    assert response.status_code == 404


@pytest.mark.django_db
def test_meetings_delete_only_target_meeting(manager: User) -> None:
    """Deleting one meeting leaves other meetings in the group untouched."""
    group = Group.objects.create(name='g')
    keep = Meeting.objects.create(
        group=group,
        title='keep',
        date=datetime.date(2026, 5, 1),
    )
    drop = Meeting.objects.create(
        group=group,
        title='drop',
        date=datetime.date(2026, 5, 8),
    )

    response = _delete(Client(), drop.id, user=manager)

    assert response.status_code == 204
    assert Meeting.objects.filter(pk=keep.id).exists()
    assert not Meeting.objects.filter(pk=drop.id).exists()
