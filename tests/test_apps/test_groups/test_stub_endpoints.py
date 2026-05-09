"""Smoke tests: verify groups app routes are wired (not 404)."""

import uuid

from django.urls import Resolver404, resolve

_GROUP_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')
_USER_ID = uuid.UUID('00000000-0000-0000-0000-000000000002')


def _resolves(path: str) -> bool:
    try:
        resolve(path)
        return True
    except Resolver404:
        return False


def test_groups_collection_route_is_wired() -> None:
    """GET/POST /api/v1/groups/ must not be 404."""
    assert _resolves('/api/v1/groups/')


def test_groups_detail_route_is_wired() -> None:
    """PATCH/DELETE /api/v1/groups/{id}/ must not be 404."""
    assert _resolves(f'/api/v1/groups/{_GROUP_ID}/')


def test_groups_pin_route_is_wired() -> None:
    """PUT/DELETE /api/v1/groups/{id}/pin/ must not be 404."""
    assert _resolves(f'/api/v1/groups/{_GROUP_ID}/pin/')


def test_groups_members_collection_route_is_wired() -> None:
    """GET/POST /api/v1/groups/{id}/members/ must not be 404."""
    assert _resolves(f'/api/v1/groups/{_GROUP_ID}/members/')


def test_groups_members_detail_route_is_wired() -> None:
    """DELETE /api/v1/groups/{id}/members/{user_id}/ must not be 404."""
    assert _resolves(f'/api/v1/groups/{_GROUP_ID}/members/{_USER_ID}/')
