"""Django admin registrations for the users app.

Inherits from Django's :class:`UserAdmin` so the change-password and
create-user flows go through ``UserCreationForm`` / ``AdminPasswordChangeForm``,
which call ``set_password`` for proper Argon2 hashing. The unfold mixin
themes the same admin pages without altering the password-handling
contract.
"""

from __future__ import annotations

import structlog
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from server.apps.users.models import User

log = structlog.get_logger()


@admin.register(User)
class UserAdmin(UnfoldModelAdmin, DjangoUserAdmin):
    """Themed user admin with hash-aware add/change forms."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    # Append the project-specific ``role`` field to Django's stock
    # fieldsets so it's editable on both the change and add screens.
    # Django's UserAdmin keeps ownership of password hashing — adding a
    # field here does NOT bypass set_password.
    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        ('Sitdown', {'fields': ('role',)}),
    )
    add_fieldsets = (
        *DjangoUserAdmin.add_fieldsets,
        ('Sitdown', {'fields': ('role',)}),
    )
