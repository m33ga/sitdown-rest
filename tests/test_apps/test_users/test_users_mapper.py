"""Unit tests for ``UserMapper``."""

from __future__ import annotations

import pytest

from server.apps.users.infra.mappers import UserMapper

from ._helpers import make_user


@pytest.mark.django_db
def test_mapper_full_name_concatenation() -> None:
    """``name`` is ``first_name + ' ' + last_name`` when both are set."""
    user = make_user(
        'alice',
        first_name='Alice',
        last_name='Smith',
        role='MANAGER',
    )

    payload = UserMapper().to_payload(user)

    assert payload.id == user.id
    assert payload.email == user.email
    assert payload.name == 'Alice Smith'
    assert payload.role == 'MANAGER'


@pytest.mark.django_db
def test_mapper_falls_back_to_username_when_blank_name() -> None:
    """``name`` falls back to ``username`` when first/last are blank."""
    user = make_user('alice', role='MEMBER')

    payload = UserMapper().to_payload(user)

    assert payload.name == 'alice'


@pytest.mark.django_db
def test_mapper_handles_only_first_name() -> None:
    """Only ``first_name`` set yields a name without a trailing space."""
    user = make_user('alice', first_name='Alice')

    payload = UserMapper().to_payload(user)

    assert payload.name == 'Alice'
