import uuid

import structlog
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
        """Return the user's full name; fall back to username when blank."""
        log.debug('user_str_called', user_id=str(self.id))
        return self.get_full_name() or self.username
