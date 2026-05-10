"""Unit tests for the groups use cases."""

from __future__ import annotations

import uuid

import pytest

from server.apps.groups.infra.mappers import GroupMapper
from server.apps.groups.infra.repository import GroupRepository
from server.apps.groups.logic.exceptions import (
    GroupNotFoundError,
    PermissionDeniedError,
)
from server.apps.groups.logic.usecases.create_group import CreateGroupUseCase
from server.apps.groups.logic.usecases.delete_group import DeleteGroupUseCase
from server.apps.groups.logic.usecases.list_groups import ListGroupsUseCase
from server.apps.groups.logic.usecases.pin_group import PinGroupUseCase
from server.apps.groups.logic.usecases.unpin_group import UnpinGroupUseCase
from server.apps.groups.logic.usecases.update_group import UpdateGroupUseCase
from server.apps.groups.logic.value_objects import (
    GroupCreatePayload,
    GroupUpdatePayload,
)
from server.apps.groups.models import (
    Group,
    ProjectMember,
    UserPinnedGroup,
)
from server.apps.users.models import User

from ._helpers import make_user


def _list_uc() -> ListGroupsUseCase:
    return ListGroupsUseCase(GroupRepository(), GroupMapper())


def _create_uc() -> CreateGroupUseCase:
    return CreateGroupUseCase(GroupRepository(), GroupMapper())


def _update_uc() -> UpdateGroupUseCase:
    return UpdateGroupUseCase(GroupRepository(), GroupMapper())


def _delete_uc() -> DeleteGroupUseCase:
    return DeleteGroupUseCase(GroupRepository())


def _pin_uc() -> PinGroupUseCase:
    return PinGroupUseCase(GroupRepository())


def _unpin_uc() -> UnpinGroupUseCase:
    return UnpinGroupUseCase(GroupRepository())


@pytest.mark.django_db
def test_list_groups_manager_sees_all() -> None:
    """MANAGER sees all groups regardless of ProjectMember rows."""
    user = make_user('m', role='MANAGER')
    Group.objects.create(name='a')
    Group.objects.create(name='b')

    result = _list_uc()(user=user, search=None, page=1, per_page=20)

    assert result.total == 2
    assert {g.name for g in result.results} == {'a', 'b'}


@pytest.mark.django_db
def test_list_groups_member_filtered() -> None:
    """MEMBER sees only groups with a ProjectMember row."""
    user = make_user('m', role='MEMBER')
    visible = Group.objects.create(name='visible')
    Group.objects.create(name='hidden')
    ProjectMember.objects.create(user=user, group=visible)

    result = _list_uc()(user=user, search=None, page=1, per_page=20)

    assert result.total == 1
    assert result.results[0].name == 'visible'


@pytest.mark.django_db
def test_list_groups_pinned_first() -> None:
    """Pinned groups come before non-pinned."""
    user = make_user('m', role='MANAGER')
    older = Group.objects.create(name='older')
    Group.objects.create(name='newer')
    UserPinnedGroup.objects.create(user=user, group=older)

    result = _list_uc()(user=user, search=None, page=1, per_page=20)

    names = [g.name for g in result.results]
    assert names == ['older', 'newer']
    assert result.results[0].pinned is True


@pytest.mark.django_db
def test_create_group_raises_on_non_manager() -> None:
    """Non-MANAGER raises PermissionDeniedError."""
    user = make_user('m', role='MEMBER')
    with pytest.raises(PermissionDeniedError):
        _create_uc()(user=user, payload=GroupCreatePayload(name='x'))


@pytest.mark.django_db
def test_create_group_manager_succeeds() -> None:
    """MANAGER successfully creates a group."""
    user = make_user('m', role='MANAGER')
    result = _create_uc()(
        user=user,
        payload=GroupCreatePayload(name='x'),
    )
    assert result.name == 'x'
    assert Group.objects.filter(name='x').exists()


@pytest.mark.django_db
def test_update_group_raises_on_not_found() -> None:
    """Updating a missing group raises GroupNotFoundError."""
    user = make_user('m', role='MANAGER')
    with pytest.raises(GroupNotFoundError):
        _update_uc()(
            user=user,
            group_id=uuid.UUID('00000000-0000-0000-0000-000000000123'),
            payload=GroupUpdatePayload(name='x'),
        )


@pytest.mark.django_db
def test_update_group_raises_on_non_manager() -> None:
    """Non-MANAGER update raises PermissionDeniedError."""
    user = make_user('m', role='MEMBER')
    group = Group.objects.create(name='x')
    with pytest.raises(PermissionDeniedError):
        _update_uc()(
            user=user,
            group_id=group.id,
            payload=GroupUpdatePayload(name='y'),
        )


@pytest.mark.django_db
def test_delete_group_cascades() -> None:
    """Deleting a group with project memberships cascades."""
    user = make_user('m', role='MANAGER')
    member = make_user('p', role='MEMBER')
    group = Group.objects.create(name='gone')
    ProjectMember.objects.create(user=member, group=group)
    UserPinnedGroup.objects.create(user=user, group=group)

    _delete_uc()(user=user, group_id=group.id)

    assert not Group.objects.filter(pk=group.id).exists()
    assert not ProjectMember.objects.filter(group=group).exists()
    assert not UserPinnedGroup.objects.filter(group=group).exists()


@pytest.mark.django_db
def test_delete_group_raises_on_not_found() -> None:
    """Deleting a missing group raises GroupNotFoundError."""
    user = make_user('m', role='MANAGER')
    with pytest.raises(GroupNotFoundError):
        _delete_uc()(
            user=user,
            group_id=uuid.UUID('00000000-0000-0000-0000-000000000999'),
        )


@pytest.mark.django_db
def test_delete_group_raises_on_non_manager() -> None:
    """Non-MANAGER delete raises PermissionDeniedError."""
    user = make_user('m', role='GUEST')
    group = Group.objects.create(name='x')
    with pytest.raises(PermissionDeniedError):
        _delete_uc()(user=user, group_id=group.id)


@pytest.mark.django_db
def test_pin_group_idempotent() -> None:
    """Pinning twice yields a single UserPinnedGroup row."""
    user = make_user('m', role='MANAGER')
    group = Group.objects.create(name='g')
    _pin_uc()(user=user, group_id=group.id)
    _pin_uc()(user=user, group_id=group.id)
    assert (
        UserPinnedGroup.objects.filter(
            user=user,
            group=group,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_pin_group_raises_on_not_found() -> None:
    """Pinning a missing group raises GroupNotFoundError."""
    user = make_user('m', role='MANAGER')
    with pytest.raises(GroupNotFoundError):
        _pin_uc()(
            user=user,
            group_id=uuid.UUID('00000000-0000-0000-0000-000000000888'),
        )


@pytest.mark.django_db
def test_pin_group_access_denied_for_non_member() -> None:
    """Non-MANAGER without ProjectMember row raises PermissionDeniedError."""
    user = make_user('m', role='MEMBER')
    group = Group.objects.create(name='g')
    with pytest.raises(PermissionDeniedError):
        _pin_uc()(user=user, group_id=group.id)


@pytest.mark.django_db
def test_unpin_group_idempotent() -> None:
    """Unpinning a non-pinned group does not raise."""
    user = make_user('m', role='MANAGER')
    group = Group.objects.create(name='g')
    _unpin_uc()(user=user, group_id=group.id)
    assert not UserPinnedGroup.objects.filter(
        user=user,
        group=group,
    ).exists()


@pytest.mark.django_db
def test_unpin_group_raises_on_not_found() -> None:
    """Unpinning a missing group raises GroupNotFoundError."""
    user = make_user('m', role='MANAGER')
    with pytest.raises(GroupNotFoundError):
        _unpin_uc()(
            user=user,
            group_id=uuid.UUID('00000000-0000-0000-0000-000000000777'),
        )


@pytest.mark.django_db
def test_unpin_group_access_denied_for_non_member() -> None:
    """Non-MANAGER without ProjectMember row raises PermissionDeniedError."""
    user = make_user('m', role='GUEST')
    group = Group.objects.create(name='g')
    with pytest.raises(PermissionDeniedError):
        _unpin_uc()(user=user, group_id=group.id)


@pytest.mark.django_db
def test_repository_get_by_id_returns_none_when_missing() -> None:
    """``GroupRepository.get_by_id`` returns None for unknown IDs."""
    repo = GroupRepository()
    assert (
        repo.get_by_id(
            uuid.UUID('00000000-0000-0000-0000-000000000444'),
        )
        is None
    )


@pytest.mark.django_db
def test_repository_search_filters_results() -> None:
    """``GroupRepository.list_for_user`` filters by case-insensitive name."""
    user = make_user('m', role='MANAGER')
    Group.objects.create(name='Falcon')
    Group.objects.create(name='Eagle')
    repo = GroupRepository()

    results, total = repo.list_for_user(
        user=user,
        role='MANAGER',
        search='falcon',
        page=1,
        per_page=20,
    )

    assert total == 1
    assert results[0].name == 'Falcon'


@pytest.mark.django_db
def test_repository_is_member_returns_false() -> None:
    """``is_member`` is False when no ProjectMember row exists."""
    user: User = make_user('m', role='MEMBER')
    group = Group.objects.create(name='g')
    repo = GroupRepository()
    assert repo.is_member(user, group) is False


@pytest.mark.django_db
def test_mapper_to_payload_without_annotation_returns_unpinned() -> None:
    """When no ``is_pinned`` annotation is present the mapper returns False."""
    group = Group.objects.create(name='g')
    payload = GroupMapper().to_payload(group)
    assert payload.pinned is False
