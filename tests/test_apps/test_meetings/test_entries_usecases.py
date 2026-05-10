"""Unit tests for the entries use cases and supporting infra."""

from __future__ import annotations

import datetime as dt
import time
import uuid

import pytest

from server.apps.groups.models import Group, ProjectMember
from server.apps.meetings.infra.mappers import MemberEntryMapper
from server.apps.meetings.infra.repository import MeetingRepository
from server.apps.meetings.logic.exceptions import (
    EntryNotFoundError,
    MeetingCompletedError,
    MeetingNotFoundError,
    PermissionDeniedError,
)
from server.apps.meetings.logic.usecases.list_entries import (
    ListEntriesUseCase,
)
from server.apps.meetings.logic.usecases.update_entry import (
    UpdateEntryUseCase,
)
from server.apps.meetings.logic.value_objects import (
    MemberEntryUpdatePayload,
)
from server.apps.meetings.models import Meeting, MemberEntry

from ._helpers import make_user


def _list_uc() -> ListEntriesUseCase:
    return ListEntriesUseCase(MeetingRepository(), MemberEntryMapper())


def _update_uc() -> UpdateEntryUseCase:
    return UpdateEntryUseCase(MeetingRepository(), MemberEntryMapper())


@pytest.mark.django_db
def test_list_entries_use_case_filters_by_access() -> None:
    """Non-MANAGER without ProjectMember row raises PermissionDeniedError."""
    user = make_user('m', role='MEMBER')
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    with pytest.raises(PermissionDeniedError):
        _list_uc()(user=user, meeting_id=meeting.id)


@pytest.mark.django_db
def test_list_entries_use_case_raises_when_meeting_missing() -> None:
    """Unknown meeting raises MeetingNotFoundError."""
    user = make_user('m', role='MANAGER')
    with pytest.raises(MeetingNotFoundError):
        _list_uc()(
            user=user,
            meeting_id=uuid.UUID(
                '00000000-0000-0000-0000-000000000111',
            ),
        )


@pytest.mark.django_db
def test_update_entry_use_case_member_own_allowed() -> None:
    """MEMBER editing their own entry succeeds."""
    user = make_user('m', role='MEMBER')
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    MemberEntry.objects.create(meeting=meeting, user=user)

    result = _update_uc()(
        user=user,
        meeting_id=meeting.id,
        target_user_id=user.id,
        payload=MemberEntryUpdatePayload(done='ok'),
    )

    assert result.done == 'ok'


@pytest.mark.django_db
def test_update_entry_use_case_member_other_forbidden() -> None:
    """MEMBER editing another user's entry raises PermissionDeniedError."""
    user = make_user('m', role='MEMBER')
    other = make_user('o', role='MEMBER')
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    MemberEntry.objects.create(meeting=meeting, user=other)

    with pytest.raises(PermissionDeniedError):
        _update_uc()(
            user=user,
            meeting_id=meeting.id,
            target_user_id=other.id,
            payload=MemberEntryUpdatePayload(done='nope'),
        )


@pytest.mark.django_db
def test_update_entry_use_case_manager_any_allowed() -> None:
    """MANAGER editing any user's entry succeeds."""
    manager = make_user('mgr', role='MANAGER')
    target = make_user('t', role='MEMBER')
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    MemberEntry.objects.create(meeting=meeting, user=target)

    result = _update_uc()(
        user=manager,
        meeting_id=meeting.id,
        target_user_id=target.id,
        payload=MemberEntryUpdatePayload(done='ok'),
    )

    assert result.done == 'ok'


@pytest.mark.django_db
def test_update_entry_use_case_guest_forbidden() -> None:
    """GUEST editing their own entry raises PermissionDeniedError."""
    user = make_user('g', role='GUEST')
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    MemberEntry.objects.create(meeting=meeting, user=user)

    with pytest.raises(PermissionDeniedError):
        _update_uc()(
            user=user,
            meeting_id=meeting.id,
            target_user_id=user.id,
            payload=MemberEntryUpdatePayload(done='nope'),
        )


@pytest.mark.django_db
def test_update_entry_use_case_completed_takes_precedence_over_role() -> None:
    """A completed meeting is read-only even for MANAGER."""
    manager = make_user('mgr', role='MANAGER')
    target = make_user('t', role='MEMBER')
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
        completed=True,
    )
    MemberEntry.objects.create(meeting=meeting, user=target)

    with pytest.raises(MeetingCompletedError):
        _update_uc()(
            user=manager,
            meeting_id=meeting.id,
            target_user_id=target.id,
            payload=MemberEntryUpdatePayload(done='nope'),
        )


@pytest.mark.django_db
def test_update_entry_use_case_meeting_not_found() -> None:
    """Unknown meeting raises MeetingNotFoundError."""
    user = make_user('mgr', role='MANAGER')
    with pytest.raises(MeetingNotFoundError):
        _update_uc()(
            user=user,
            meeting_id=uuid.UUID(
                '00000000-0000-0000-0000-000000000333',
            ),
            target_user_id=user.id,
            payload=MemberEntryUpdatePayload(done='x'),
        )


@pytest.mark.django_db
def test_update_entry_use_case_entry_not_found() -> None:
    """Meeting exists but no entry for target_user_id → EntryNotFoundError."""
    user = make_user('mgr', role='MANAGER')
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    with pytest.raises(EntryNotFoundError):
        _update_uc()(
            user=user,
            meeting_id=meeting.id,
            target_user_id=uuid.UUID(
                '00000000-0000-0000-0000-000000000444',
            ),
            payload=MemberEntryUpdatePayload(done='x'),
        )


@pytest.mark.django_db
def test_repository_update_entry_partial() -> None:
    """update_entry leaves untouched fields alone."""
    repo = MeetingRepository()
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    user = make_user('alice', role='MEMBER')
    entry = MemberEntry.objects.create(
        meeting=meeting,
        user=user,
        promised='p',
        done='d',
    )

    repo.update_entry(
        entry,
        promised=None,
        done='d2',
        will_do=None,
        discussion=None,
        notes=None,
    )

    entry.refresh_from_db()
    assert entry.promised == 'p'
    assert entry.done == 'd2'


@pytest.mark.django_db
def test_repository_update_entry_noop_does_not_bump_updated_at() -> None:
    """A no-op update_entry leaves updated_at intact."""
    repo = MeetingRepository()
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    user = make_user('alice', role='MEMBER')
    entry = MemberEntry.objects.create(meeting=meeting, user=user)
    original = entry.updated_at

    # Force a small delay so a real save() would clearly bump
    # updated_at, making this assertion meaningful.
    time.sleep(0.05)

    repo.update_entry(
        entry,
        promised=None,
        done=None,
        will_do=None,
        discussion=None,
        notes=None,
    )

    entry.refresh_from_db()
    assert entry.updated_at == original


@pytest.mark.django_db
def test_repository_update_entry_bumps_updated_at_on_change() -> None:
    """A real change DOES bump updated_at via auto_now."""
    repo = MeetingRepository()
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    user = make_user('alice', role='MEMBER')
    entry = MemberEntry.objects.create(meeting=meeting, user=user)
    original = entry.updated_at
    time.sleep(0.05)

    repo.update_entry(
        entry,
        promised=None,
        done='changed',
        will_do=None,
        discussion=None,
        notes=None,
    )

    entry.refresh_from_db()
    assert entry.updated_at > original


@pytest.mark.django_db
def test_member_entry_mapper_passes_through_fields() -> None:
    """Mapper copies all fields without mutation."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=dt.date(2026, 5, 1),
    )
    user = make_user('alice', role='MEMBER')
    entry = MemberEntry.objects.create(
        meeting=meeting,
        user=user,
        promised='p',
        done='d',
        will_do='w',
        discussion='di',
        notes='n',
    )

    payload = MemberEntryMapper().to_payload(entry)

    assert payload.id == entry.id
    assert payload.meeting_id == meeting.id
    assert payload.user_id == user.id
    assert payload.promised == 'p'
    assert payload.done == 'd'
    assert payload.will_do == 'w'
    assert payload.discussion == 'di'
    assert payload.notes == 'n'
