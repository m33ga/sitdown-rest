import uuid

import structlog
from django.conf import settings
from django.db import models

log = structlog.get_logger()


class Group(models.Model):
    """A named project group that contains meetings and members."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        log.debug('group_str_called', group_id=str(self.pk))
        return self.name


class UserPinnedGroup(models.Model):
    """Records which groups a user has pinned (many-to-many via explicit table)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pinned_groups',
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='pinned_by',
    )

    class Meta:
        unique_together = (('user', 'group'),)


class ProjectMember(models.Model):
    """Records which users belong to a group as project members."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_memberships',
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='members',
    )

    class Meta:
        unique_together = (('user', 'group'),)
