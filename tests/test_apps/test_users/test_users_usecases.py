"""Unit tests for ``ListUsersUseCase``."""

from __future__ import annotations

import pytest

from server.apps.users.infra.mappers import UserMapper
from server.apps.users.infra.repository import UserRepository
from server.apps.users.logic.exceptions import PermissionDeniedError
from server.apps.users.logic.usecases.list_users import ListUsersUseCase

from ._helpers import make_user


def _uc() -> ListUsersUseCase:
    return ListUsersUseCase(UserRepository(), UserMapper())


@pytest.mark.django_db
def test_use_case_manager_returns_paginated_payload() -> None:
    """MANAGER receives a populated payload with correct pagination metadata."""
    manager = make_user('mgr', role='MANAGER')
    make_user('alice', role='MEMBER')
    make_user('bob', role='MEMBER')

    result = _uc()(
        user=manager,
        search=None,
        page=1,
        per_page=10,
    )

    assert result.total == 3
    assert result.page == 1
    assert result.per_page == 10
    assert {u.email for u in result.results} == {
        manager.email,
        'alice@example.com',
        'bob@example.com',
    }


@pytest.mark.django_db
def test_use_case_member_forbidden() -> None:
    """A MEMBER caller raises ``PermissionDeniedError``."""
    member = make_user('mem', role='MEMBER')

    with pytest.raises(PermissionDeniedError):
        _uc()(
            user=member,
            search=None,
            page=1,
            per_page=10,
        )


@pytest.mark.django_db
def test_use_case_guest_forbidden() -> None:
    """A GUEST caller raises ``PermissionDeniedError``."""
    guest = make_user('g', role='GUEST')

    with pytest.raises(PermissionDeniedError):
        _uc()(
            user=guest,
            search=None,
            page=1,
            per_page=10,
        )


@pytest.mark.django_db
def test_use_case_search_forwarded() -> None:
    """Search is forwarded to the repository verbatim."""
    manager = make_user('mgr', role='MANAGER', first_name='Bob')
    make_user('alice', role='MEMBER', first_name='Alice')

    result = _uc()(
        user=manager,
        search='ali',
        page=1,
        per_page=10,
    )

    assert result.total == 1
    assert result.results[0].name == 'Alice'


@pytest.mark.django_db
def test_use_case_page_per_page_forwarded() -> None:
    """``page`` and ``per_page`` are forwarded into the payload metadata."""
    manager = make_user('mgr', role='MANAGER')

    result = _uc()(
        user=manager,
        search=None,
        page=3,
        per_page=5,
    )

    assert result.page == 3
    assert result.per_page == 5
    # Page 3 with 1 user / per_page=5 -> empty slice but total=1.
    assert result.total == 1
    assert result.results == []
