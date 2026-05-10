from __future__ import annotations

import uuid

import msgspec


class TokenCreatePayload(msgspec.Struct, frozen=True):
    """Request payload for POST /token."""

    username: str
    password: str


class TokenResponse(msgspec.Struct, frozen=True):
    """Response payload for POST /token."""

    access_token: str
    refresh_token: str


class TokenRefreshPayload(msgspec.Struct, frozen=True):
    """Request payload for POST /token/refresh."""

    refresh_token: str


class TokenRefreshResponse(msgspec.Struct, frozen=True):
    """Response payload for POST /token/refresh."""

    access_token: str
    refresh_token: str


class UserPayload(msgspec.Struct, frozen=True):
    """A single user in the organisation directory."""

    id: uuid.UUID
    email: str
    name: str
    role: str  # TODO: replace with Role enum in domain models milestone


class PaginatedUsersPayload(msgspec.Struct, frozen=True):
    """Response payload for GET /users."""

    results: list[UserPayload]
    total: int
    page: int
    per_page: int
