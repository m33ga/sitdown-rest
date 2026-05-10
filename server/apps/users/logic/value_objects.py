from __future__ import annotations

import uuid

import msgspec


class UserPayload(msgspec.Struct, frozen=True):
    """A single user in the organisation directory."""

    id: uuid.UUID
    email: str
    name: str
    # ``role`` is kept as ``str`` (rather than ``User.Role`` or a shared
    # enum) to avoid a cross-app import that would break the
    # apps-independence import-linter contract. Values are stable per the
    # OpenAPI schema (MANAGER | MEMBER | GUEST).
    role: str


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
