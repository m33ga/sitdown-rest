"""Mapper between ``User`` ORM rows and the directory response payload."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.users.logic.value_objects import UserPayload

if TYPE_CHECKING:
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(slots=True, frozen=True)
class UserMapper:
    """Translate ``User`` ORM instances into directory payloads."""

    def to_payload(self, user: User) -> UserPayload:
        """Map a ``User`` row to a ``UserPayload``.

        ``name`` is computed from ``first_name + last_name`` via
        ``get_full_name()``; falls back to ``username`` when both are
        blank (mirrors :class:`ProjectMemberMapper` in the groups app).
        """
        log.debug(
            'user_mapper_to_payload_called',
            user_id=str(user.id),
        )
        return UserPayload(
            id=user.id,
            email=user.email,
            name=user.get_full_name() or user.username,
            role=user.role,
        )
