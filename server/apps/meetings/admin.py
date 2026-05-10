"""Django admin registrations for the meetings app."""

from __future__ import annotations

import structlog
from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from server.apps.meetings.models import Meeting, MemberEntry

log = structlog.get_logger()


@admin.register(Meeting)
class MeetingAdmin(UnfoldModelAdmin):
    """Standup meeting admin."""

    list_display = ('id', 'group', 'title', 'date', 'completed')
    list_filter = ('completed', 'group')
    search_fields = ('title', 'group__name')
    date_hierarchy = 'date'
    raw_id_fields = ('group',)
    readonly_fields = ('id',)


@admin.register(MemberEntry)
class MemberEntryAdmin(UnfoldModelAdmin):
    """Per-member meeting entry admin."""

    list_display = ('id', 'meeting', 'user', 'updated_at')
    list_filter = ('meeting__group',)
    search_fields = (
        'meeting__title',
        'user__username',
        'user__email',
    )
    raw_id_fields = ('meeting', 'user')
    readonly_fields = ('id', 'updated_at')
