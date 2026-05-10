"""Tests for Group, UserPinnedGroup, and ProjectMember models."""

import pytest
from django.db import IntegrityError

from server.apps.groups.models import Group, ProjectMember, UserPinnedGroup
from server.apps.users.models import User


def _make_user(username: str) -> User:
    return User.objects.create_user(username=username, password='x')


@pytest.mark.django_db
def test_group_str() -> None:
    """Group __str__ returns the group name."""
    group = Group.objects.create(name='Backend')
    assert str(group) == 'Backend'


@pytest.mark.django_db
def test_group_created_at_auto() -> None:
    """Group.created_at is set automatically on creation."""
    group = Group.objects.create(name='Frontend')
    assert group.created_at is not None


@pytest.mark.django_db
def test_userpinnedgroup_unique() -> None:
    """Duplicate (user, group) pair on UserPinnedGroup raises IntegrityError."""
    user = _make_user('alice')
    group = Group.objects.create(name='Alpha')
    UserPinnedGroup.objects.create(user=user, group=group)
    with pytest.raises(IntegrityError):
        UserPinnedGroup.objects.create(user=user, group=group)


@pytest.mark.django_db
def test_projectmember_unique() -> None:
    """Duplicate (user, group) pair on ProjectMember raises IntegrityError."""
    user = _make_user('bob')
    group = Group.objects.create(name='Beta')
    ProjectMember.objects.create(user=user, group=group)
    with pytest.raises(IntegrityError):
        ProjectMember.objects.create(user=user, group=group)
