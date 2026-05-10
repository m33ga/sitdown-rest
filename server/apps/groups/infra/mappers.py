"""Mappers between groups-domain ORM instances and value-object payloads."""

from __future__ import annotations

import attrs
import structlog

from server.apps.groups.logic.value_objects import (
    GroupCreatedPayload,
    GroupPayload,
    ProjectMemberRecordPayload,
)
from server.apps.groups.models import Group, ProjectMember

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


@attrs.define(slots=True, frozen=True)
class ProjectMemberMapper:
    """Translate ``ProjectMember`` rows into membership response payloads."""

    def to_payload(
        self,
        member: ProjectMember,
    ) -> ProjectMemberRecordPayload:
        """Map a ``ProjectMember`` to its API payload.

        Note: ``payload.id`` is the **user's** UUID, not the membership
        row id. Clients identify a member by who they are, not by the
        membership row's surrogate id (matches the openapi.yaml example).
        """
        log.debug(
            'project_member_mapper_to_payload_called',
            user_id=str(member.user_id),
            group_id=str(member.group_id),
        )
        user = member.user
        return ProjectMemberRecordPayload(
            id=user.id,
            email=user.email,
            name=user.get_full_name() or user.username,
            role=user.role,
        )
