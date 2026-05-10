"""Django admin registrations for the groups app."""

from __future__ import annotations

import structlog
from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from server.apps.groups.models import Group, ProjectMember, UserPinnedGroup

log = structlog.get_logger()


@admin.register(Group)
class GroupAdmin(UnfoldModelAdmin):
    """Project group admin."""

    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')


@admin.register(ProjectMember)
class ProjectMemberAdmin(UnfoldModelAdmin):
    """Project membership admin."""

    list_display = ('id', 'user', 'group')
    list_filter = ('group',)
    search_fields = ('user__username', 'user__email', 'group__name')
    raw_id_fields = ('user', 'group')
    readonly_fields = ('id',)


@admin.register(UserPinnedGroup)
class UserPinnedGroupAdmin(UnfoldModelAdmin):
    """User pin admin (per-user group bookmarking)."""

    list_display = ('id', 'user', 'group')
    list_filter = ('group',)
    search_fields = ('user__username', 'user__email', 'group__name')
    raw_id_fields = ('user', 'group')
    readonly_fields = ('id',)
