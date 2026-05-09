from django.apps import AppConfig


class MeetingsConfig(AppConfig):
    """Django app config for the meetings app."""

    name = 'server.apps.meetings'
    default_auto_field = 'django.db.models.UUIDField'
