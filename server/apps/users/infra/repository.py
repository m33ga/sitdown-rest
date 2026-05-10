"""Repository for the users domain (read-only directory).

Users are managed exclusively through the Django admin; this repository
exposes the queries needed to render the read-only directory endpoint.
"""

from __future__ import annotations

import attrs
import structlog
from django.db.models import Q

from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(slots=True)
class UserRepository:
    """ORM wrapper for the read-only ``User`` directory."""

    def list(
        self,
        *,
        search: str | None,
        page: int,
        per_page: int,
    ) -> tuple[list[User], int]:
        """Return ``(page slice, total count)`` for the directory query.

        Search semantics: case-insensitive substring match against
        ``first_name``, ``last_name``, or ``email``. ``name`` is a
        serializer-level computed field, so we approximate by splitting
        across the two stored name parts. Whitespace-only or empty search
        values must be normalised to ``None`` by the caller.
        """
        log.debug(
            'user_repo_list_called',
            search=search,
            page=page,
            per_page=per_page,
        )
        qs = User.objects.all()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search),
            )
        qs = qs.order_by('username')
        total = qs.count()
        offset = (page - 1) * per_page
        results = list(qs[offset : offset + per_page])
        log.debug(
            'user_repo_list_done',
            total=total,
            returned=len(results),
        )
        return results, total
