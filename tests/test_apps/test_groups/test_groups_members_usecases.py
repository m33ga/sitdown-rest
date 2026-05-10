"""Unit tests for the members use cases and supporting infra."""

from __future__ import annotations

import uuid

import pytest

from server.apps.groups.infra.mappers import (
    GroupMapper,
    ProjectMemberMapper,
)
from server.apps.groups.infra.repository import GroupRepository
from server.apps.groups.logic.exceptions import (
    GroupNotFoundError,
    MemberAlreadyExistsError,
    MemberNotFoundError,
    PermissionDeniedError,
    UserNotFoundError,
)
from server.apps.groups.logic.usecases.add_member import AddMemberUseCase
from server.apps.groups.logic.usecases.list_members import (
    ListMembersUseCase,
)
from server.apps.groups.logic.usecases.remove_member import (
    RemoveMemberUseCase,
)
from server.apps.groups.logic.value_objects import AddMemberPayload
from server.apps.groups.models import Group, ProjectMember

from ._helpers import make_user

# Suppress unused-import warning for GroupMapper (kept for symmetry with the
# DI list, in case the file grows tests for both mappers later).
_ = GroupMapper


def _list_uc() -> ListMembersUseCase:
    return ListMembersUseCase(GroupRepository(), ProjectMemberMapper())


def _add_uc() -> AddMemberUseCase:
    return AddMemberUseCase(GroupRepository(), ProjectMemberMapper())


def _remove_uc() -> RemoveMemberUseCase:
    return RemoveMemberUseCase(GroupRepository())


@pytest.mark.django_db
def test_list_members_use_case_filters_by_access() -> None:
    """Non-MANAGER without ProjectMember row raises PermissionDeniedError."""
    user = make_user('m', role='MEMBER')
    group = Group.objects.create(name='g')
    with pytest.raises(PermissionDeniedError):
        _list_uc()(user=user, group_id=group.id)


@pytest.mark.django_db
def test_list_members_use_case_raises_when_group_missing() -> None:
    """Unknown group_id raises GroupNotFoundError."""
    user = make_user('m', role='MANAGER')
    with pytest.raises(GroupNotFoundError):
        _list_uc()(
            user=user,
            group_id=uuid.UUID('00000000-0000-0000-0000-000000000111'),
        )


@pytest.mark.django_db
def test_add_member_use_case_raises_on_non_manager() -> None:
    """Non-MANAGER add raises PermissionDeniedError."""
    user = make_user('m', role='MEMBER')
    group = Group.objects.create(name='g')
    target = make_user('t', role='MEMBER')
    with pytest.raises(PermissionDeniedError):
        _add_uc()(
            user=user,
            group_id=group.id,
            payload=AddMemberPayload(user_id=target.id),
        )


@pytest.mark.django_db
def test_add_member_use_case_raises_on_unknown_user() -> None:
    """Unknown user_id raises UserNotFoundError."""
    user = make_user('m', role='MANAGER')
    group = Group.objects.create(name='g')
    with pytest.raises(UserNotFoundError):
        _add_uc()(
            user=user,
            group_id=group.id,
            payload=AddMemberPayload(
                user_id=uuid.UUID(
                    '00000000-0000-0000-0000-000000000999',
                ),
            ),
        )


@pytest.mark.django_db
def test_add_member_use_case_raises_on_duplicate() -> None:
    """Re-adding the same user raises MemberAlreadyExistsError."""
    user = make_user('m', role='MANAGER')
    group = Group.objects.create(name='g')
    target = make_user('t', role='MEMBER')
    _add_uc()(
        user=user,
        group_id=group.id,
        payload=AddMemberPayload(user_id=target.id),
    )
    with pytest.raises(MemberAlreadyExistsError):
        _add_uc()(
            user=user,
            group_id=group.id,
            payload=AddMemberPayload(user_id=target.id),
        )


@pytest.mark.django_db
def test_add_member_use_case_raises_on_missing_group() -> None:
    """Unknown group raises GroupNotFoundError before user lookup."""
    user = make_user('m', role='MANAGER')
    target = make_user('t', role='MEMBER')
    with pytest.raises(GroupNotFoundError):
        _add_uc()(
            user=user,
            group_id=uuid.UUID(
                '00000000-0000-0000-0000-000000000222',
            ),
            payload=AddMemberPayload(user_id=target.id),
        )


@pytest.mark.django_db
def test_remove_member_use_case_raises_on_non_manager() -> None:
    """Non-MANAGER remove raises PermissionDeniedError."""
    user = make_user('m', role='MEMBER')
    group = Group.objects.create(name='g')
    target = make_user('t', role='MEMBER')
    with pytest.raises(PermissionDeniedError):
        _remove_uc()(user=user, group_id=group.id, target_user_id=target.id)


@pytest.mark.django_db
def test_remove_member_use_case_raises_when_not_a_member() -> None:
    """Removing a non-member raises MemberNotFoundError."""
    user = make_user('m', role='MANAGER')
    group = Group.objects.create(name='g')
    not_member = make_user('out', role='MEMBER')
    with pytest.raises(MemberNotFoundError):
        _remove_uc()(
            user=user,
            group_id=group.id,
            target_user_id=not_member.id,
        )


@pytest.mark.django_db
def test_remove_member_use_case_raises_on_missing_group() -> None:
    """Unknown group raises GroupNotFoundError."""
    user = make_user('m', role='MANAGER')
    target = make_user('t', role='MEMBER')
    with pytest.raises(GroupNotFoundError):
        _remove_uc()(
            user=user,
            group_id=uuid.UUID(
                '00000000-0000-0000-0000-000000000333',
            ),
            target_user_id=target.id,
        )


@pytest.mark.django_db
def test_repository_list_members_orders_by_username() -> None:
    """list_members returns rows ordered by user__username."""
    repo = GroupRepository()
    group = Group.objects.create(name='g')
    ProjectMember.objects.create(
        group=group,
        user=make_user('charlie', role='MEMBER'),
    )
    ProjectMember.objects.create(
        group=group,
        user=make_user('alice', role='MEMBER'),
    )
    ProjectMember.objects.create(
        group=group,
        user=make_user('bob', role='MEMBER'),
    )

    members = repo.list_members(group)

    usernames = [m.user.username for m in members]
    assert usernames == ['alice', 'bob', 'charlie']


@pytest.mark.django_db
def test_repository_get_member_returns_none_when_missing() -> None:
    """get_member returns None when (group, user_id) has no row."""
    repo = GroupRepository()
    group = Group.objects.create(name='g')
    assert repo.get_member(
        group,
        uuid.UUID('00000000-0000-0000-0000-000000000444'),
    ) is None


@pytest.mark.django_db
def test_repository_get_member_returns_row_when_present() -> None:
    """get_member returns the row when it exists."""
    repo = GroupRepository()
    group = Group.objects.create(name='g')
    target = make_user('alice', role='MEMBER')
    ProjectMember.objects.create(group=group, user=target)
    member = repo.get_member(group, target.id)
    assert member is not None
    assert member.user_id == target.id


@pytest.mark.django_db
def test_repository_add_member_returns_with_user_attached() -> None:
    """add_member returns a ProjectMember with the User pre-loaded."""
    repo = GroupRepository()
    group = Group.objects.create(name='g')
    target = make_user('alice', role='MEMBER')
    member = repo.add_member(group, target.id)
    assert member.user.email == 'alice@example.com'
    assert member.user.role == 'MEMBER'


@pytest.mark.django_db
def test_mapper_uses_user_id_in_payload() -> None:
    """ProjectMemberMapper writes user_id (not membership_id) in the id field."""
    group = Group.objects.create(name='g')
    target = make_user('alice', role='MEMBER')
    member = ProjectMember.objects.create(group=group, user=target)
    mapper = ProjectMemberMapper()

    payload = mapper.to_payload(member)

    assert payload.id == target.id
    assert payload.id != member.id
    assert payload.email == 'alice@example.com'
    assert payload.role == 'MEMBER'


@pytest.mark.django_db
def test_mapper_uses_full_name_when_set() -> None:
    """Mapper prefers get_full_name() over username when first/last set."""
    group = Group.objects.create(name='g')
    user = make_user('alice', role='MEMBER')
    user.first_name = 'Alice'
    user.last_name = 'Wonderland'
    user.save(update_fields=['first_name', 'last_name'])
    member = ProjectMember.objects.create(group=group, user=user)

    payload = ProjectMemberMapper().to_payload(member)

    assert payload.name == 'Alice Wonderland'


@pytest.mark.django_db
def test_mapper_falls_back_to_username() -> None:
    """Mapper falls back to username when no first/last name is set."""
    group = Group.objects.create(name='g')
    user = make_user('charlie', role='GUEST')
    member = ProjectMember.objects.create(group=group, user=user)

    payload = ProjectMemberMapper().to_payload(member)

    assert payload.name == 'charlie'
