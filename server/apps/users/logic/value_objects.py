from __future__ import annotations

import uuid

import msgspec


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


class ErrorResponse(msgspec.Struct, frozen=True):
    """Standard error response per openapi.yaml ErrorResponse schema."""

    error: str
    message: str
