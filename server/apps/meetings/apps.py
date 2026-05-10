from django.apps import AppConfig
from django.apps import apps as django_apps
from django.db.models.signals import post_save


class MeetingsConfig(AppConfig):
    """Django app config for the meetings app."""

    name = 'server.apps.meetings'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self) -> None:
        """Connect cross-app signal receivers once models are loaded.

        ``groups`` precedes ``meetings`` in ``INSTALLED_APPS``, so its
        ``ProjectMember`` model is already registered when this hook fires.
        Importing it via ``apps.get_model`` (instead of a Python import)
        is what keeps the apps-independence import-linter contract green.
        """
        from server.apps.meetings.signals import (
            create_entries_for_new_member,
        )

        project_member = django_apps.get_model('groups', 'ProjectMember')
        post_save.connect(
            create_entries_for_new_member,
            sender=project_member,
            dispatch_uid='meetings.create_entries_for_new_member',
        )
