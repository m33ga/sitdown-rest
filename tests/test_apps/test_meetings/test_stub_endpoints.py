"""Smoke tests: verify meetings app routes are wired (not 404)."""

import uuid

from django.urls import Resolver404, resolve

_GROUP_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')
_MEETING_ID = uuid.UUID('00000000-0000-0000-0000-000000000002')
_USER_ID = uuid.UUID('00000000-0000-0000-0000-000000000003')


def _resolves(path: str) -> bool:
    try:
        resolve(path)
        return True
    except Resolver404:
        return False


def test_meetings_collection_route_is_wired() -> None:
    """GET/POST /api/v1/groups/{group_id}/meetings/ must not be 404."""
    assert _resolves(f'/api/v1/groups/{_GROUP_ID}/meetings/')


def test_meetings_detail_route_is_wired() -> None:
    """PATCH/DELETE /api/v1/meetings/{id}/ must not be 404."""
    assert _resolves(f'/api/v1/meetings/{_MEETING_ID}/')


def test_entries_collection_route_is_wired() -> None:
    """GET /api/v1/meetings/{id}/entries/ must not be 404."""
    assert _resolves(f'/api/v1/meetings/{_MEETING_ID}/entries/')


def test_entries_detail_route_is_wired() -> None:
    """PATCH /api/v1/meetings/{id}/entries/{user_id}/ must not be 404."""
    assert _resolves(f'/api/v1/meetings/{_MEETING_ID}/entries/{_USER_ID}/')


def test_nonexistent_route_not_wired() -> None:
    """Unknown paths must not resolve."""
    assert not _resolves('/api/v1/does-not-exist/')
