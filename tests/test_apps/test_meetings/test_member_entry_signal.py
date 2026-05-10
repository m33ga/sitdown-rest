"""Tests for the ProjectMember post_save signal that backfills entries."""

from __future__ import annotations

import datetime

import pytest

from server.apps.groups.models import Group, ProjectMember
from server.apps.meetings.models import Meeting, MemberEntry

from ._helpers import make_user


@pytest.mark.django_db
def test_signal_creates_entries_for_new_member_in_open_meetings() -> None:
    """Adding a non-GUEST member backfills entries in every open meeting."""
    group = Group.objects.create(name='g')
    open_a = Meeting.objects.create(
        group=group,
        title='a',
        date=datetime.date(2026, 5, 1),
    )
    open_b = Meeting.objects.create(
        group=group,
        title='b',
        date=datetime.date(2026, 5, 8),
    )
    user = make_user('alice', role='MEMBER')

    ProjectMember.objects.create(group=group, user=user)

    entries = MemberEntry.objects.filter(user=user).order_by('meeting__date')
    assert [e.meeting_id for e in entries] == [open_a.id, open_b.id]
    assert all(e.promised == '' for e in entries)


@pytest.mark.django_db
def test_signal_skips_completed_meetings() -> None:
    """Completed meetings stay untouched when a new member is added."""
    group = Group.objects.create(name='g')
    Meeting.objects.create(
        group=group,
        title='done',
        date=datetime.date(2026, 5, 1),
        completed=True,
    )
    user = make_user('bob', role='MEMBER')

    ProjectMember.objects.create(group=group, user=user)

    assert not MemberEntry.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_signal_skips_guests() -> None:
    """GUEST users never receive eager entries."""
    group = Group.objects.create(name='g')
    Meeting.objects.create(
        group=group,
        title='m',
        date=datetime.date(2026, 5, 1),
    )
    guest = make_user('eve', role='GUEST')

    ProjectMember.objects.create(group=group, user=guest)

    assert not MemberEntry.objects.filter(user=guest).exists()


@pytest.mark.django_db
def test_signal_carries_over_latest_will_do() -> None:
    """The new member's `promised` is their latest non-empty `will_do`."""
    group = Group.objects.create(name='g')
    earlier = Meeting.objects.create(
        group=group,
        title='earlier',
        date=datetime.date(2026, 5, 1),
    )
    later = Meeting.objects.create(
        group=group,
        title='later',
        date=datetime.date(2026, 5, 8),
    )
    user = make_user('carol', role='MEMBER')
    # Pre-existing entries from a prior membership.
    MemberEntry.objects.create(
        meeting=earlier,
        user=user,
        will_do='ship A',
    )
    MemberEntry.objects.create(
        meeting=later,
        user=user,
        will_do='ship B',
    )
    fresh = Meeting.objects.create(
        group=group,
        title='fresh',
        date=datetime.date(2026, 5, 15),
    )

    ProjectMember.objects.create(group=group, user=user)

    entry = MemberEntry.objects.get(meeting=fresh, user=user)
    assert entry.promised == 'ship B'


@pytest.mark.django_db
def test_signal_is_idempotent_on_re_add() -> None:
    """Removing and re-adding a member keeps the existing entries unchanged."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m',
        date=datetime.date(2026, 5, 1),
    )
    user = make_user('dan', role='MEMBER')

    membership = ProjectMember.objects.create(group=group, user=user)
    entry = MemberEntry.objects.get(meeting=meeting, user=user)
    entry.done = 'finished X'
    entry.save(update_fields=['done'])

    membership.delete()
    ProjectMember.objects.create(group=group, user=user)

    surviving = MemberEntry.objects.get(meeting=meeting, user=user)
    assert surviving.done == 'finished X'
    assert MemberEntry.objects.filter(meeting=meeting, user=user).count() == 1


@pytest.mark.django_db
def test_signal_noop_on_membership_save_update() -> None:
    """Saving an existing ProjectMember (created=False) does not re-fire."""
    group = Group.objects.create(name='g')
    Meeting.objects.create(
        group=group,
        title='m',
        date=datetime.date(2026, 5, 1),
    )
    user = make_user('frank', role='MEMBER')
    membership = ProjectMember.objects.create(group=group, user=user)
    before = MemberEntry.objects.filter(user=user).count()

    membership.save()

    assert MemberEntry.objects.filter(user=user).count() == before
