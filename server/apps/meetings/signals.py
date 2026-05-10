"""Signal receivers for the meetings app.

Cross-app coordination point: when a ``ProjectMember`` is added to a
group, we want a ``MemberEntry`` to appear in every still-open meeting
of that group so the SPA can render the new member alongside existing
ones. ``server.apps.groups`` must not import from ``server.apps.meetings``
(import-linter "apps independence" contract), so the wiring lives here
and is connected in ``MeetingsConfig.ready()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from django.db import transaction

from server.apps.meetings.models import Meeting, MemberEntry

if TYPE_CHECKING:
    from server.apps.groups.models import ProjectMember

log = structlog.get_logger()


def create_entries_for_new_member(
    sender: type[ProjectMember],
    *,
    instance: ProjectMember,
    created: bool,
    **kwargs: object,
) -> None:
    """Eagerly create ``MemberEntry`` rows for newly-added members.

    Fires on ``ProjectMember`` post_save. No-op on updates (``created=False``)
    and on GUEST users (who never get entries by project convention).

    ``bulk_create(..., ignore_conflicts=True)`` keeps re-add idempotent:
    if a user was removed and re-added, the prior ``MemberEntry`` rows
    are reused (they cascade-deleted with ``ProjectMember`` only if FKs
    were wired that way — they aren't — so the rows survive and the
    unique ``(meeting, user)`` constraint would otherwise raise).
    """
    user = instance.user
    if not created:
        log.debug(
            'member_entry_signal_skip_not_created',
            user_id=str(user.pk),
            group_id=str(instance.group_id),
        )
        return
    if user.role == 'GUEST':
        log.debug(
            'member_entry_signal_skip_guest',
            user_id=str(user.pk),
            group_id=str(instance.group_id),
        )
        return
    log.debug(
        'member_entry_signal_called',
        user_id=str(user.pk),
        group_id=str(instance.group_id),
    )
    meetings = list(
        Meeting.objects.filter(
            group_id=instance.group_id,
            completed=False,
        ),
    )
    if not meetings:
        log.debug(
            'member_entry_signal_no_open_meetings',
            user_id=str(user.pk),
            group_id=str(instance.group_id),
        )
        return
    promised = _latest_will_do(instance.group_id, user.pk)
    entries = [
        MemberEntry(
            meeting=meeting,
            user=user,
            promised=promised,
        )
        for meeting in meetings
    ]
    with transaction.atomic():
        MemberEntry.objects.bulk_create(entries, ignore_conflicts=True)
    log.debug(
        'member_entry_signal_done',
        user_id=str(user.pk),
        group_id=str(instance.group_id),
        count=len(entries),
    )


def _latest_will_do(group_id: object, user_id: object) -> str:
    """Return the user's most recent non-empty ``will_do`` in ``group``.

    Mirrors ``MeetingRepository._collect_carry_over`` for a single user.
    Falls back to ``''`` when there is no prior entry.
    """
    row = (
        MemberEntry.objects
        .filter(
            meeting__group_id=group_id,
            user_id=user_id,
        )
        .exclude(will_do='')
        .order_by('-meeting__date', '-updated_at')
        .values_list('will_do', flat=True)
        .first()
    )
    return row or ''
