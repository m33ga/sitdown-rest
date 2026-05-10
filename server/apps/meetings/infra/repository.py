"""Repository for the meetings domain.

Cross-app reads (``Group`` / ``ProjectMember`` from ``server.apps.groups``)
go through ``django.apps.apps.get_model`` to keep the apps-independence
import-linter contract clean. The same pattern is used elsewhere for
``django.contrib.auth.get_user_model``.
"""

from __future__ import annotations

import datetime as _date_module
from typing import TYPE_CHECKING
from uuid import UUID

import attrs
import structlog
from django.apps import apps as django_apps
from django.db import IntegrityError, transaction

from server.apps.meetings.logic.exceptions import MeetingDateConflictError
from server.apps.meetings.models import Meeting, MemberEntry

if TYPE_CHECKING:
    from server.apps.groups.models import Group, ProjectMember
    from server.apps.users.models import User

log = structlog.get_logger()


def _group_model() -> type[Group]:
    return django_apps.get_model('groups', 'Group')


def _project_member_model() -> type[ProjectMember]:
    return django_apps.get_model('groups', 'ProjectMember')


@attrs.define(slots=True)
class MeetingRepository:
    """ORM wrapper for ``Meeting`` plus the eager ``MemberEntry`` flow."""

    def get_group(self, group_id: UUID) -> Group | None:
        """Return the group with ``id == group_id`` or ``None``."""
        log.debug('meeting_repo_get_group_called', group_id=str(group_id))
        try:
            group = _group_model().objects.get(pk=group_id)
        except _group_model().DoesNotExist:
            log.debug(
                'meeting_repo_get_group_not_found',
                group_id=str(group_id),
            )
            return None
        log.debug('meeting_repo_get_group_found', group_id=str(group_id))
        return group

    def has_access(
        self,
        user: User,
        role: str,
        group: Group,
    ) -> bool:
        """Return ``True`` iff ``user`` may read meetings of ``group``."""
        log.debug(
            'meeting_repo_has_access_called',
            user_id=str(user.pk),
            role=role,
            group_id=str(group.id),
        )
        if role == 'MANAGER':
            log.debug('meeting_repo_has_access_manager')
            return True
        result = _project_member_model().objects.filter(
            user=user,
            group=group,
        ).exists()
        log.debug('meeting_repo_has_access_result', result=result)
        return result

    def list_for_group(
        self,
        group: Group,
        page: int,
        per_page: int,
    ) -> tuple[list[Meeting], int]:
        """Return ``(page slice, total count)`` ordered by ``date`` desc."""
        log.debug(
            'meeting_repo_list_called',
            group_id=str(group.id),
            page=page,
            per_page=per_page,
        )
        qs = Meeting.objects.filter(group=group).order_by('-date', '-id')
        total = qs.count()
        offset = (page - 1) * per_page
        results = list(qs[offset:offset + per_page])
        log.debug(
            'meeting_repo_list_done',
            group_id=str(group.id),
            total=total,
            returned=len(results),
        )
        return results, total

    def get_by_id(self, meeting_id: UUID) -> Meeting | None:
        """Return the meeting with ``id == meeting_id`` or ``None``."""
        log.debug(
            'meeting_repo_get_called',
            meeting_id=str(meeting_id),
        )
        try:
            meeting = Meeting.objects.get(pk=meeting_id)
        except Meeting.DoesNotExist:
            log.debug(
                'meeting_repo_get_not_found',
                meeting_id=str(meeting_id),
            )
            return None
        log.debug(
            'meeting_repo_get_found',
            meeting_id=str(meeting_id),
        )
        return meeting

    def create_with_entries(
        self,
        group: Group,
        *,
        title: str,
        date: _date_module.date,
    ) -> Meeting:
        """Create a meeting + eager MemberEntry rows in a single transaction.

        - One ``MemberEntry`` per **non-GUEST** ``ProjectMember`` of ``group``.
        - Each entry's ``promised`` is the user's most recent non-empty
          ``will_do`` across all earlier meetings in this same group, or
          ``''`` if no prior entry exists.
        - Raises ``MeetingDateConflictError`` if the unique
          ``(group, date)`` constraint is violated.
        """
        log.debug(
            'meeting_repo_create_called',
            group_id=str(group.id),
            date=str(date),
        )
        with transaction.atomic():
            try:
                meeting = Meeting.objects.create(
                    group=group,
                    title=title,
                    date=date,
                )
            except IntegrityError:
                log.debug(
                    'meeting_repo_create_date_conflict',
                    group_id=str(group.id),
                    date=str(date),
                )
                raise MeetingDateConflictError from None
            members = list(
                group.members
                .exclude(user__role='GUEST')
                .select_related('user'),
            )
            log.debug(
                'meeting_repo_create_resolved_members',
                count=len(members),
            )
            user_ids = [m.user_id for m in members]
            carry = self._collect_carry_over(group, user_ids)
            log.debug(
                'meeting_repo_create_carry_over_resolved',
                count=len(carry),
            )
            entries = [
                MemberEntry(
                    meeting=meeting,
                    user=member.user,
                    promised=carry.get(member.user_id, ''),
                )
                for member in members
            ]
            if entries:
                MemberEntry.objects.bulk_create(entries)
        log.debug(
            'meeting_repo_create_done',
            meeting_id=str(meeting.id),
            entries=len(entries),
        )
        return meeting

    def _collect_carry_over(
        self,
        group: Group,
        user_ids: list[UUID],
    ) -> dict[UUID, str]:
        """Latest non-empty ``will_do`` per user across ``group``'s meetings."""
        if not user_ids:
            return {}
        prior = (
            MemberEntry.objects
            .filter(
                meeting__group_id=group.id,
                user_id__in=user_ids,
            )
            .exclude(will_do='')
            .order_by('user_id', '-meeting__date', '-updated_at')
            .values_list('user_id', 'will_do')
        )
        carry: dict[UUID, str] = {}
        for user_id, will_do in prior:
            carry.setdefault(user_id, will_do)
        return carry

    def update(
        self,
        meeting: Meeting,
        *,
        title: str | None,
        date: _date_module.date | None,
        completed: bool | None,
    ) -> Meeting:
        """Apply partial updates and persist; raise on date collisions."""
        log.debug(
            'meeting_repo_update_called',
            meeting_id=str(meeting.id),
            has_title=title is not None,
            has_date=date is not None,
            has_completed=completed is not None,
        )
        update_fields: list[str] = []
        if title is not None:
            meeting.title = title
            update_fields.append('title')
        if date is not None:
            meeting.date = date
            update_fields.append('date')
        if completed is not None:
            meeting.completed = completed
            update_fields.append('completed')
        if not update_fields:
            log.debug('meeting_repo_update_noop', meeting_id=str(meeting.id))
            return meeting
        try:
            with transaction.atomic():
                meeting.save(update_fields=update_fields)
        except IntegrityError:
            log.debug(
                'meeting_repo_update_date_conflict',
                meeting_id=str(meeting.id),
            )
            raise MeetingDateConflictError from None
        log.debug(
            'meeting_repo_update_done',
            meeting_id=str(meeting.id),
            fields=update_fields,
        )
        return meeting

    def delete(self, meeting: Meeting) -> None:
        """Delete ``meeting`` and cascade-delete its ``MemberEntry`` rows."""
        log.debug(
            'meeting_repo_delete_called',
            meeting_id=str(meeting.id),
        )
        meeting.delete()
        log.debug('meeting_repo_delete_done')
