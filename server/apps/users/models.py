import uuid

import structlog
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

log = structlog.get_logger()


class User(AbstractUser):
    """Custom user model with UUID PK and role field."""

    class Role(models.TextChoices):
        MANAGER = 'MANAGER', 'Manager'
        MEMBER = 'MEMBER', 'Member'
        GUEST = 'GUEST', 'Guest'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.GUEST,
    )

    def __str__(self) -> str:
        log.debug('user_str_called', user_id=str(self.id))
        return self.get_full_name() or self.username


class RefreshToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='refresh_tokens',
    )
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
