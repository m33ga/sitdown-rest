from __future__ import annotations

import datetime
import uuid

import msgspec


class GroupPayload(msgspec.Struct, frozen=True):
    """A group as returned in list responses (includes per-user pinned flag)."""

    id: uuid.UUID
    name: str
    created_at: datetime.datetime
    pinned: bool


class GroupCreatedPayload(msgspec.Struct, frozen=True):
    """Returned when a group is created or updated (no pinned field)."""

    id: uuid.UUID
    name: str
    created_at: datetime.datetime


class GroupCreatePayload(msgspec.Struct, frozen=True):
    """Request payload for POST /groups."""

    name: str


class GroupUpdatePayload(msgspec.Struct, frozen=True):
    """Request payload for PATCH /groups/{id}. All fields optional."""

    name: str | None = None


class PaginatedGroupsPayload(msgspec.Struct, frozen=True):
    """Response payload for GET /groups."""

    results: list[GroupPayload]
    total: int
    page: int
    per_page: int


class ProjectMemberRecordPayload(msgspec.Struct, frozen=True):
    """A project membership record."""

    id: uuid.UUID
    email: str
    name: str
    role: str  # TODO: replace with Role enum in domain models milestone


class AddMemberPayload(msgspec.Struct, frozen=True):
    """Request payload for POST /groups/{id}/members."""

    user_id: uuid.UUID


class ErrorResponse(msgspec.Struct, frozen=True):
    """Standard error envelope returned for 4xx responses."""

    error: str
    message: str
