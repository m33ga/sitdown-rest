"""Mappers between ``Group`` ORM instances and value-object payloads."""

from __future__ import annotations

import attrs
import structlog

from server.apps.groups.logic.value_objects import (
    GroupCreatedPayload,
    GroupPayload,
)
from server.apps.groups.models import Group

log = structlog.get_logger()


@attrs.define(slots=True, frozen=True)
class GroupMapper:
    """Translate ``Group`` ORM instances into msgspec response payloads."""

    def to_payload(self, group: Group) -> GroupPayload:
        """Map a (possibly-annotated) ``Group`` to a list-response payload.

        Reads ``is_pinned`` from the queryset annotation added by
        :meth:`GroupRepository.list_for_user` and falls back to ``False``
        when the attribute is absent.
        """
        log.debug(
            'group_mapper_to_payload_called',
            group_id=str(group.id),
        )
        return GroupPayload(
            id=group.id,
            name=group.name,
            created_at=group.created_at,
            pinned=getattr(group, 'is_pinned', False),
        )

    def to_created_payload(self, group: Group) -> GroupCreatedPayload:
        """Map a ``Group`` to the create/update response payload."""
        log.debug(
            'group_mapper_to_created_payload_called',
            group_id=str(group.id),
        )
        return GroupCreatedPayload(
            id=group.id,
            name=group.name,
            created_at=group.created_at,
        )
