"""Tests for Meeting and MemberEntry models."""

import datetime

import pytest
from django.db import IntegrityError

from server.apps.groups.models import Group
from server.apps.meetings.models import Meeting, MemberEntry
from server.apps.users.models import User


def _make_user(username: str) -> User:
    return User.objects.create_user(username=username, password='x')


def _make_group(name: str) -> Group:
    return Group.objects.create(name=name)


@pytest.mark.django_db
def test_meeting_str() -> None:
    """Meeting __str__ includes title and date."""
    group = _make_group('Alpha')
    meeting = Meeting.objects.create(
        group=group,
        title='Daily',
        date=datetime.date(2026, 5, 10),
    )
    assert str(meeting) == 'Daily (2026-05-10)'


@pytest.mark.django_db
def test_meeting_completed_default_false() -> None:
    """Meeting.completed defaults to False."""
    group = _make_group('Beta')
    meeting = Meeting.objects.create(
        group=group,
        title='Standup',
        date=datetime.date(2026, 5, 11),
    )
    assert meeting.completed is False


@pytest.mark.django_db
def test_meeting_same_group_date_allowed() -> None:
    """Two meetings in the same group on the same date now coexist."""
    group = _make_group('Gamma')
    day = datetime.date(2026, 5, 12)
    Meeting.objects.create(group=group, title='First', date=day)
    Meeting.objects.create(group=group, title='Second', date=day)
    assert Meeting.objects.filter(group=group, date=day).count() == 2


@pytest.mark.django_db
def test_memberentry_unique_per_meeting_user() -> None:
    """Duplicate (meeting, user) pair on MemberEntry raises IntegrityError."""
    group = _make_group('Delta')
    user = _make_user('alice')
    meeting = Meeting.objects.create(
        group=group,
        title='Sync',
        date=datetime.date(2026, 5, 13),
    )
    MemberEntry.objects.create(meeting=meeting, user=user)
    with pytest.raises(IntegrityError):
        MemberEntry.objects.create(meeting=meeting, user=user)


@pytest.mark.django_db
def test_memberentry_text_fields_default_blank() -> None:
    """All five text fields default to empty string."""
    group = _make_group('Epsilon')
    user = _make_user('bob')
    meeting = Meeting.objects.create(
        group=group,
        title='Daily',
        date=datetime.date(2026, 5, 14),
    )
    entry = MemberEntry.objects.create(meeting=meeting, user=user)
    assert entry.promised == ''
    assert entry.done == ''
    assert entry.will_do == ''
    assert entry.discussion == ''
    assert entry.notes == ''


@pytest.mark.django_db
def test_memberentry_updated_at_auto() -> None:
    """MemberEntry.updated_at is populated automatically on save."""
    group = _make_group('Zeta')
    user = _make_user('charlie')
    meeting = Meeting.objects.create(
        group=group,
        title='Standup',
        date=datetime.date(2026, 5, 15),
    )
    entry = MemberEntry.objects.create(meeting=meeting, user=user)
    assert entry.updated_at is not None
