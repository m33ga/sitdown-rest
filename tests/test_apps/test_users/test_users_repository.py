"""Unit tests for ``UserRepository``."""

from __future__ import annotations

import pytest

from server.apps.users.infra.repository import UserRepository

from ._helpers import make_user


@pytest.mark.django_db
def test_repo_list_no_search_returns_all_ordered_by_username() -> None:
    """No search returns every user ordered by ``username`` ascending."""
    make_user('charlie')
    make_user('alice')
    make_user('bob')

    results, total = UserRepository().list(
        search=None,
        page=1,
        per_page=10,
    )

    assert total == 3
    assert [u.username for u in results] == ['alice', 'bob', 'charlie']


@pytest.mark.django_db
def test_repo_list_pagination_slices_correctly() -> None:
    """``page=2, per_page=2`` returns the right slice plus the full total."""
    for username in ['u1', 'u2', 'u3', 'u4', 'u5']:
        make_user(username)

    results, total = UserRepository().list(
        search=None,
        page=2,
        per_page=2,
    )

    assert total == 5
    assert [u.username for u in results] == ['u3', 'u4']


@pytest.mark.django_db
def test_repo_list_search_first_name_case_insensitive() -> None:
    """Search matches partial first_name irrespective of case."""
    make_user('a', first_name='Alice', last_name='Smith')
    make_user('b', first_name='Bob', last_name='Brown')

    results, total = UserRepository().list(
        search='ali',
        page=1,
        per_page=10,
    )

    assert total == 1
    assert results[0].first_name == 'Alice'


@pytest.mark.django_db
def test_repo_list_search_last_name_case_insensitive() -> None:
    """Search matches partial last_name irrespective of case."""
    make_user('a', first_name='Alice', last_name='Smith')
    make_user('b', first_name='Bob', last_name='Brown')

    results, total = UserRepository().list(
        search='SMI',
        page=1,
        per_page=10,
    )

    assert total == 1
    assert results[0].last_name == 'Smith'


@pytest.mark.django_db
def test_repo_list_search_email_case_insensitive() -> None:
    """Search matches partial email irrespective of case."""
    make_user('alice', email='alice@company.com')
    make_user('bob', email='bob@other.org')

    results, total = UserRepository().list(
        search='COMPANY',
        page=1,
        per_page=10,
    )

    assert total == 1
    assert results[0].email == 'alice@company.com'


@pytest.mark.django_db
def test_repo_list_search_no_matches_returns_empty() -> None:
    """A search with no matches returns ``([], 0)``."""
    make_user('alice')
    make_user('bob')

    results, total = UserRepository().list(
        search='zzz-no-match',
        page=1,
        per_page=10,
    )

    assert total == 0
    assert results == []


@pytest.mark.django_db
def test_repo_list_none_search_treated_as_no_filter() -> None:
    """``search=None`` returns all users (caller normalises empty strings)."""
    make_user('a')
    make_user('b')

    results, total = UserRepository().list(
        search=None,
        page=1,
        per_page=10,
    )

    assert total == 2
    assert len(results) == 2


@pytest.mark.django_db
def test_repo_list_out_of_range_page_returns_empty_with_total() -> None:
    """A page far past the last record returns ``[]`` with the correct total."""
    make_user('alice')

    results, total = UserRepository().list(
        search=None,
        page=999,
        per_page=10,
    )

    assert total == 1
    assert results == []
