import uuid

import structlog
from django.conf import settings
from django.db import models

log = structlog.get_logger()


class Meeting(models.Model):
    """A single standup meeting event belonging to a group."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='meetings',
    )
    title = models.CharField(max_length=255)
    date = models.DateField()
    completed = models.BooleanField(default=False)

    def __str__(self) -> str:
        """Return the meeting's title plus its date."""
        log.debug('meeting_str_called', meeting_id=str(self.pk))
        return f'{self.title} ({self.date})'


class MemberEntry(models.Model):
    """Per-member standup entry inside a meeting.

    Holds the five structured text sections (promised / done / will_do /
    discussion / notes) one user filled out for one meeting.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name='entries',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='standup_entries',
    )
    updated_at = models.DateTimeField(auto_now=True)
    promised = models.TextField(blank=True, default='')
    done = models.TextField(blank=True, default='')
    will_do = models.TextField(blank=True, default='')
    discussion = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')

    class Meta:
        unique_together = (('meeting', 'user'),)
