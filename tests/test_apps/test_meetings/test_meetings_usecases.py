"""Unit tests for the meetings use cases and supporting infra."""

from __future__ import annotations

import datetime
import uuid

import pytest

from server.apps.groups.models import Group, ProjectMember
from server.apps.meetings.infra.mappers import MeetingMapper
from server.apps.meetings.infra.repository import MeetingRepository
from server.apps.meetings.logic.exceptions import (
    GroupNotFoundError,
    MeetingDateConflictError,
    MeetingNotFoundError,
    PermissionDeniedError,
)
from server.apps.meetings.logic.usecases.create_meeting import (
    CreateMeetingUseCase,
)
from server.apps.meetings.logic.usecases.delete_meeting import (
    DeleteMeetingUseCase,
)
from server.apps.meetings.logic.usecases.list_meetings import (
    ListMeetingsUseCase,
)
from server.apps.meetings.logic.usecases.update_meeting import (
    UpdateMeetingUseCase,
)
from server.apps.meetings.logic.value_objects import (
    MeetingCreatePayload,
    MeetingUpdatePayload,
)
from server.apps.meetings.models import Meeting, MemberEntry

from ._helpers import make_user


def _list_uc() -> ListMeetingsUseCase:
    return ListMeetingsUseCase(MeetingRepository(), MeetingMapper())


def _create_uc() -> CreateMeetingUseCase:
    return CreateMeetingUseCase(MeetingRepository(), MeetingMapper())


def _update_uc() -> UpdateMeetingUseCase:
    return UpdateMeetingUseCase(MeetingRepository(), MeetingMapper())


def _delete_uc() -> DeleteMeetingUseCase:
    return DeleteMeetingUseCase(MeetingRepository())


@pytest.mark.django_db
def test_list_meetings_use_case_filters_by_access() -> None:
    """Non-MANAGER without ProjectMember row raises PermissionDeniedError."""
    user = make_user('m', role='MEMBER')
    group = Group.objects.create(name='g')
    with pytest.raises(PermissionDeniedError):
        _list_uc()(user=user, group_id=group.id, page=1, per_page=20)


@pytest.mark.django_db
def test_list_meetings_use_case_raises_when_group_missing() -> None:
    """Unknown group_id raises GroupNotFoundError."""
    user = make_user('m', role='MANAGER')
    with pytest.raises(GroupNotFoundError):
        _list_uc()(
            user=user,
            group_id=uuid.UUID('00000000-0000-0000-0000-000000000111'),
            page=1,
            per_page=20,
        )


@pytest.mark.django_db
def test_create_meeting_use_case_raises_on_non_manager() -> None:
    """Non-MANAGER creating a meeting raises PermissionDeniedError."""
    user = make_user('m', role='MEMBER')
    group = Group.objects.create(name='g')
    with pytest.raises(PermissionDeniedError):
        _create_uc()(
            user=user,
            group_id=group.id,
            payload=MeetingCreatePayload(date=datetime.date(2026, 5, 1)),
        )


@pytest.mark.django_db
def test_create_meeting_use_case_raises_on_missing_group() -> None:
    """Unknown group raises GroupNotFoundError before doing any DB writes."""
    user = make_user('m', role='MANAGER')
    with pytest.raises(GroupNotFoundError):
        _create_uc()(
            user=user,
            group_id=uuid.UUID(
                '00000000-0000-0000-0000-000000000222',
            ),
            payload=MeetingCreatePayload(date=datetime.date(2026, 5, 1)),
        )


@pytest.mark.django_db
def test_update_meeting_use_case_raises_on_not_found() -> None:
    """Unknown meeting raises MeetingNotFoundError."""
    user = make_user('m', role='MANAGER')
    with pytest.raises(MeetingNotFoundError):
        _update_uc()(
            user=user,
            meeting_id=uuid.UUID(
                '00000000-0000-0000-0000-000000000333',
            ),
            payload=MeetingUpdatePayload(completed=True),
        )


@pytest.mark.django_db
def test_update_meeting_use_case_raises_on_non_manager() -> None:
    """Non-MANAGER update raises PermissionDeniedError."""
    user = make_user('m', role='MEMBER')
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )
    with pytest.raises(PermissionDeniedError):
        _update_uc()(
            user=user,
            meeting_id=meeting.id,
            payload=MeetingUpdatePayload(completed=True),
        )


@pytest.mark.django_db
def test_delete_meeting_use_case_raises_on_not_found() -> None:
    """Deleting a missing meeting raises MeetingNotFoundError."""
    user = make_user('m', role='MANAGER')
    with pytest.raises(MeetingNotFoundError):
        _delete_uc()(
            user=user,
            meeting_id=uuid.UUID(
                '00000000-0000-0000-0000-000000000444',
            ),
        )


@pytest.mark.django_db
def test_delete_meeting_use_case_raises_on_non_manager() -> None:
    """Non-MANAGER delete raises PermissionDeniedError."""
    user = make_user('m', role='GUEST')
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )
    with pytest.raises(PermissionDeniedError):
        _delete_uc()(user=user, meeting_id=meeting.id)


@pytest.mark.django_db
def test_repository_create_with_entries_excludes_guests() -> None:
    """create_with_entries does NOT create a MemberEntry for GUEST users."""
    repo = MeetingRepository()
    group = Group.objects.create(name='g')
    member_user = make_user('alice', role='MEMBER')
    guest_user = make_user('bob', role='GUEST')
    ProjectMember.objects.create(group=group, user=member_user)
    ProjectMember.objects.create(group=group, user=guest_user)

    meeting = repo.create_with_entries(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )

    user_ids = set(
        MemberEntry.objects.filter(meeting=meeting).values_list(
            'user_id', flat=True
        ),
    )
    assert user_ids == {member_user.id}


@pytest.mark.django_db
def test_repository_create_raises_on_duplicate_date() -> None:
    """A second create with same (group, date) raises the conflict error."""
    repo = MeetingRepository()
    group = Group.objects.create(name='g')
    repo.create_with_entries(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )
    with pytest.raises(MeetingDateConflictError):
        repo.create_with_entries(
            group=group,
            title='m2',
            date=datetime.date(2026, 5, 1),
        )


@pytest.mark.django_db
def test_repository_update_raises_on_duplicate_date() -> None:
    """Updating a meeting's date to a taken slot raises the conflict error."""
    repo = MeetingRepository()
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
    with pytest.raises(MeetingDateConflictError):
        repo.update(
            other,
            title=None,
            date=datetime.date(2026, 5, 1),
            completed=None,
        )


@pytest.mark.django_db
def test_repository_carry_over_picks_latest_will_do() -> None:
    """The carry-over collects the most recent non-empty will_do per user."""
    repo = MeetingRepository()
    group = Group.objects.create(name='g')
    user = make_user('alice', role='MEMBER')
    ProjectMember.objects.create(group=group, user=user)

    earlier = Meeting.objects.create(
        group=group,
        title='earlier',
        date=datetime.date(2026, 4, 1),
    )
    MemberEntry.objects.create(
        meeting=earlier,
        user=user,
        will_do='task A',
    )
    later = Meeting.objects.create(
        group=group,
        title='later',
        date=datetime.date(2026, 4, 15),
    )
    MemberEntry.objects.create(
        meeting=later,
        user=user,
        will_do='task B',
    )

    meeting = repo.create_with_entries(
        group=group,
        title='new',
        date=datetime.date(2026, 5, 1),
    )

    entry = MemberEntry.objects.get(meeting=meeting, user=user)
    assert entry.promised == 'task B'


@pytest.mark.django_db
def test_repository_carry_over_skips_empty_will_do() -> None:
    """Empty will_do strings are NOT used as carry-over source."""
    repo = MeetingRepository()
    group = Group.objects.create(name='g')
    user = make_user('alice', role='MEMBER')
    ProjectMember.objects.create(group=group, user=user)

    earlier = Meeting.objects.create(
        group=group,
        title='earlier',
        date=datetime.date(2026, 4, 1),
    )
    MemberEntry.objects.create(
        meeting=earlier,
        user=user,
        will_do='task A',
    )
    later = Meeting.objects.create(
        group=group,
        title='later',
        date=datetime.date(2026, 4, 15),
    )
    MemberEntry.objects.create(
        meeting=later,
        user=user,
        will_do='',
    )

    meeting = repo.create_with_entries(
        group=group,
        title='new',
        date=datetime.date(2026, 5, 1),
    )

    entry = MemberEntry.objects.get(meeting=meeting, user=user)
    assert entry.promised == 'task A'


@pytest.mark.django_db
def test_repository_update_noop_returns_meeting_unchanged() -> None:
    """Update with all-None payload skips the save and returns the meeting."""
    repo = MeetingRepository()
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
    )
    result = repo.update(
        meeting,
        title=None,
        date=None,
        completed=None,
    )
    assert result.id == meeting.id


@pytest.mark.django_db
def test_mapper_passes_through_fields() -> None:
    """Mapper copies id, group_id, title, date, completed without changes."""
    group = Group.objects.create(name='g')
    meeting = Meeting.objects.create(
        group=group,
        title='m1',
        date=datetime.date(2026, 5, 1),
        completed=True,
    )
    payload = MeetingMapper().to_payload(meeting)
    assert payload.id == meeting.id
    assert payload.group_id == group.id
    assert payload.title == 'm1'
    assert payload.date == datetime.date(2026, 5, 1)
    assert payload.completed is True
