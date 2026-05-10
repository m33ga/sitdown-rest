"""Shared fixtures for meetings API tests."""

from __future__ import annotations

import pytest

from server.apps.users.models import User

from ._helpers import make_user


@pytest.fixture
def manager(db: None) -> User:
    """A persisted MANAGER user."""
    return make_user('manager', role='MANAGER')


@pytest.fixture
def member(db: None) -> User:
    """A persisted MEMBER user."""
    return make_user('member', role='MEMBER')


@pytest.fixture
def guest(db: None) -> User:
    """A persisted GUEST user."""
    return make_user('guest', role='GUEST')
