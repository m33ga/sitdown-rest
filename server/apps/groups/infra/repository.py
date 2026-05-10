"""Repository for the groups domain.

Provides CRUD plus per-user pin and membership queries against the Django ORM.
The list query annotates each ``Group`` with an ``is_pinned`` boolean computed
from the ``UserPinnedGroup`` M2M for the requesting user, then orders pinned
results first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import attrs
import structlog
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef

from server.apps.groups.logic.exceptions import (
    MemberAlreadyExistsError,
    MemberNotFoundError,
    UserNotFoundError,
)
from server.apps.groups.models import Group, ProjectMember, UserPinnedGroup

if TYPE_CHECKING:
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(slots=True)
class GroupRepository:
    """ORM wrapper for ``Group`` plus pin and project-member queries."""

    def list_for_user(
        self,
        user: User,
        role: str,
        search: str | None,
        page: int,
        per_page: int,
    ) -> tuple[list[Group], int]:
        """Return (annotated groups for this page, total matching count)."""
        log.debug(
            'group_repo_list_called',
            user_id=str(user.id),
            role=role,
            search=search,
            page=page,
            per_page=per_page,
        )
        qs = Group.objects.all()
        if role != 'MANAGER':
            qs = qs.filter(members__user=user)
        if search:
            qs = qs.filter(name__icontains=search)
        qs = (
            qs
            .annotate(
                is_pinned=Exists(
                    UserPinnedGroup.objects.filter(
                        user=user,
                        group=OuterRef('pk'),
                    ),
                ),
            )
            .order_by('-is_pinned', '-created_at')
            .distinct()
        )
        total = qs.count()
        offset = (page - 1) * per_page
        results = list(qs[offset : offset + per_page])
        log.debug('group_repo_list_done', total=total, returned=len(results))
        return results, total

    def get_by_id(self, group_id: UUID) -> Group | None:
        """Return the group with ``id == group_id`` or ``None`` if missing."""
        log.debug('group_repo_get_called', group_id=str(group_id))
        try:
            group = Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            log.debug('group_repo_get_not_found', group_id=str(group_id))
            return None
        log.debug('group_repo_get_found', group_id=str(group_id))
        return group

    def create(self, name: str) -> Group:
        """Create and return a new group with ``name``."""
        log.debug('group_repo_create_called', name=name)
        group = Group.objects.create(name=name)
        log.debug('group_repo_created', group_id=str(group.id))
        return group

    def update(self, group: Group, name: str) -> Group:
        """Rename ``group`` to ``name`` and persist the change."""
        log.debug('group_repo_update_called', group_id=str(group.id))
        group.name = name
        group.save(update_fields=['name'])
        log.debug('group_repo_updated', group_id=str(group.id))
        return group

    def delete(self, group: Group) -> None:
        """Delete ``group`` and all dependent rows (cascade)."""
        log.debug('group_repo_delete_called', group_id=str(group.id))
        group.delete()
        log.debug('group_repo_deleted')

    def pin(self, user: User, group: Group) -> None:
        """Pin ``group`` for ``user``. Idempotent — no-op if already pinned."""
        log.debug(
            'group_repo_pin_called',
            user_id=str(user.id),
            group_id=str(group.id),
        )
        UserPinnedGroup.objects.get_or_create(user=user, group=group)
        log.debug('group_repo_pinned')

    def unpin(self, user: User, group: Group) -> None:
        """Remove the pin of ``group`` for ``user``. Idempotent."""
        log.debug(
            'group_repo_unpin_called',
            user_id=str(user.id),
            group_id=str(group.id),
        )
        UserPinnedGroup.objects.filter(user=user, group=group).delete()
        log.debug('group_repo_unpinned')

    def is_member(self, user: User, group: Group) -> bool:
        """Return ``True`` iff ``user`` is a ProjectMember of ``group``."""
        log.debug(
            'group_repo_is_member_called',
            user_id=str(user.id),
            group_id=str(group.id),
        )
        result = ProjectMember.objects.filter(
            user=user,
            group=group,
        ).exists()
        log.debug('group_repo_is_member_result', result=result)
        return result

    def list_members(self, group: Group) -> list[ProjectMember]:
        """Return all ProjectMember rows for ``group``, ordered by username.

        Uses ``select_related('user')`` so the mapper can read ``user.email``,
        ``user.role``, etc. without N+1 queries.
        """
        log.debug('group_repo_list_members_called', group_id=str(group.id))
        results = list(
            ProjectMember.objects
            .filter(group=group)
            .select_related('user')
            .order_by('user__username'),
        )
        log.debug(
            'group_repo_list_members_done',
            group_id=str(group.id),
            count=len(results),
        )
        return results

    def get_member(
        self,
        group: Group,
        user_id: UUID,
    ) -> ProjectMember | None:
        """Return the ProjectMember for ``(group, user_id)`` or ``None``."""
        log.debug(
            'group_repo_get_member_called',
            group_id=str(group.id),
            user_id=str(user_id),
        )
        try:
            member = ProjectMember.objects.select_related('user').get(
                group=group, user_id=user_id
            )
        except ProjectMember.DoesNotExist:
            log.debug(
                'group_repo_get_member_not_found',
                group_id=str(group.id),
                user_id=str(user_id),
            )
            return None
        log.debug('group_repo_get_member_found', user_id=str(user_id))
        return member

    def add_member(self, group: Group, user_id: UUID) -> ProjectMember:
        """Create a ProjectMember row for ``(group, user_id)``.

        Raises:
            UserNotFoundError: ``user_id`` doesn't match any existing user.
            MemberAlreadyExistsError: ``(group, user)`` is already in the
                ``ProjectMember`` table.
        """
        log.debug(
            'group_repo_add_member_called',
            group_id=str(group.id),
            user_id=str(user_id),
        )
        user_model = get_user_model()
        try:
            user_obj = user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            log.debug(
                'group_repo_add_member_user_not_found',
                user_id=str(user_id),
            )
            raise UserNotFoundError from None
        try:
            with transaction.atomic():
                member = ProjectMember.objects.create(
                    group=group,
                    user=user_obj,
                )
        except IntegrityError:
            log.debug(
                'group_repo_add_member_duplicate',
                group_id=str(group.id),
                user_id=str(user_id),
            )
            raise MemberAlreadyExistsError from None
        log.debug(
            'group_repo_add_member_created',
            membership_id=str(member.id),
        )
        return member

    def remove_member(self, group: Group, user_id: UUID) -> None:
        """Delete the ProjectMember row for ``(group, user_id)``.

        Raises:
            MemberNotFoundError: no membership row exists for the pair.
        """
        log.debug(
            'group_repo_remove_member_called',
            group_id=str(group.id),
            user_id=str(user_id),
        )
        deleted, _ = ProjectMember.objects.filter(
            group=group,
            user_id=user_id,
        ).delete()
        if deleted == 0:
            log.debug(
                'group_repo_remove_member_not_found',
                group_id=str(group.id),
                user_id=str(user_id),
            )
            raise MemberNotFoundError
        log.debug(
            'group_repo_remove_member_done',
            group_id=str(group.id),
            user_id=str(user_id),
        )
