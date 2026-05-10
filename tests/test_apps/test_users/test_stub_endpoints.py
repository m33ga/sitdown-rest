"""Smoke tests: verify users app routes are wired (not 404)."""

from django.urls import Resolver404, resolve


def _resolves(path: str) -> bool:
    try:
        resolve(path)
        return True
    except Resolver404:
        return False


def test_token_create_route_is_wired() -> None:
    """POST /api/v1/token/ must not be 404."""
    assert _resolves('/api/v1/token/')


def test_token_refresh_route_is_wired() -> None:
    """POST /api/v1/token/refresh/ must not be 404."""
    assert _resolves('/api/v1/token/refresh/')


def test_users_list_route_is_wired() -> None:
    """GET /api/v1/users/ must not be 404."""
    assert _resolves('/api/v1/users/')
