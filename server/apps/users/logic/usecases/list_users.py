"""Use case for ``GET /users``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.users.logic.exceptions import PermissionDeniedError
from server.apps.users.logic.value_objects import PaginatedUsersPayload

if TYPE_CHECKING:
    from server.apps.users.infra.mappers import UserMapper
    from server.apps.users.infra.repository import UserRepository
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class ListUsersUseCase:
    """Return the paginated org-wide user directory (MANAGER only)."""

    _user_repo: UserRepository
    _user_mapper: UserMapper

    def __call__(
        self,
        *,
        user: User,
        search: str | None,
        page: int,
        per_page: int,
    ) -> PaginatedUsersPayload:
        """Run the use case and return a paginated payload.

        Raises:
            PermissionDeniedError: ``user.role`` is not ``MANAGER``.
        """
        log.debug(
            'list_users_called',
            user_id=str(user.id),
            role=user.role,
            search=search,
            page=page,
            per_page=per_page,
        )
        if user.role != 'MANAGER':
            log.debug('list_users_forbidden', role=user.role)
            raise PermissionDeniedError
        users, total = self._user_repo.list(
            search=search,
            page=page,
            per_page=per_page,
        )
        results = [self._user_mapper.to_payload(u) for u in users]
        log.debug(
            'list_users_done',
            count=len(results),
            total=total,
        )
        return PaginatedUsersPayload(
            results=results,
            total=total,
            page=page,
            per_page=per_page,
        )
