"""Verify that migration tables are created and the schema is consistent."""

import pytest
from django.db import connection


@pytest.mark.django_db
def test_users_table_exists() -> None:
    """users_user and users_refreshtoken tables must exist."""
    tables = connection.introspection.table_names()
    assert 'users_user' in tables
    assert 'users_refreshtoken' in tables


@pytest.mark.django_db
def test_groups_tables_exist() -> None:
    """groups_group, _userpinnedgroup, _projectmember tables must exist."""
    tables = connection.introspection.table_names()
    assert 'groups_group' in tables
    assert 'groups_userpinnedgroup' in tables
    assert 'groups_projectmember' in tables


@pytest.mark.django_db
def test_meetings_tables_exist() -> None:
    """meetings_meeting and meetings_memberentry tables must exist."""
    tables = connection.introspection.table_names()
    assert 'meetings_meeting' in tables
    assert 'meetings_memberentry' in tables
