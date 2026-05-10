"""Tests for the User model."""

import uuid

import pytest
from django.db import IntegrityError

from server.apps.users.models import User


@pytest.mark.django_db
def test_user_role_choices() -> None:
    """Role TextChoices must match spec values."""
    assert User.Role.MANAGER == 'MANAGER'
    assert User.Role.MEMBER == 'MEMBER'
    assert User.Role.GUEST == 'GUEST'


@pytest.mark.django_db
def test_user_uuid_pk() -> None:
    """Primary key is a UUID instance."""
    user = User.objects.create_user(username='alice', password='x')
    assert isinstance(user.id, uuid.UUID)


@pytest.mark.django_db
def test_user_role_default() -> None:
    """Newly created users default to GUEST role."""
    user = User.objects.create_user(username='guest_user', password='x')
    assert user.role == User.Role.GUEST


@pytest.mark.django_db
def test_user_str_with_full_name() -> None:
    """__str__ returns full name when first/last name are set."""
    user = User.objects.create_user(
        username='bob',
        first_name='Bob',
        last_name='Smith',
        password='x',
    )
    assert str(user) == 'Bob Smith'


@pytest.mark.django_db
def test_user_str_without_name() -> None:
    """__str__ falls back to username when no full name is set."""
    user = User.objects.create_user(username='charlie', password='x')
    assert str(user) == 'charlie'


@pytest.mark.django_db
def test_user_email_unique() -> None:
    """Two users with the same email raise IntegrityError."""
    User.objects.create_user(
        username='user1',
        email='dupe@example.com',
        password='x',
    )
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            username='user2',
            email='dupe@example.com',
            password='x',
        )
