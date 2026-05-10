from __future__ import annotations

import datetime
import uuid

import msgspec


class MeetingPayload(msgspec.Struct, frozen=True):
    """A single standup meeting."""

    id: uuid.UUID
    group_id: uuid.UUID
    title: str
    date: datetime.date
    completed: bool


class MeetingCreatePayload(msgspec.Struct, frozen=True):
    """Request payload for POST /groups/{group_id}/meetings."""

    date: datetime.date
    title: str | None = None


class MeetingUpdatePayload(msgspec.Struct, frozen=True):
    """Request payload for PATCH /meetings/{id}. All fields optional."""

    title: str | None = None
    date: datetime.date | None = None
    completed: bool | None = None


class PaginatedMeetingsPayload(msgspec.Struct, frozen=True):
    """Response payload for GET /groups/{group_id}/meetings."""

    results: list[MeetingPayload]
    total: int
    page: int
    per_page: int


class MemberEntryPayload(msgspec.Struct, frozen=True):
    """One member's standup tab inside a meeting."""

    id: uuid.UUID
    meeting_id: uuid.UUID
    user_id: uuid.UUID
    updated_at: datetime.datetime
    promised: str
    done: str
    will_do: str
    discussion: str
    notes: str


class MemberEntryUpdatePayload(msgspec.Struct, frozen=True):
    """Request payload for PATCH /meetings/{id}/entries/{user_id}."""

    promised: str | None = None
    done: str | None = None
    will_do: str | None = None
    discussion: str | None = None
    notes: str | None = None


class ErrorResponse(msgspec.Struct, frozen=True):
    """Standard error envelope returned for 4xx responses."""

    error: str
    message: str
