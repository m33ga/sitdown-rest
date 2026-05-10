"""Use case for ``GET /groups``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import structlog

from server.apps.groups.infra.mappers import GroupMapper
from server.apps.groups.infra.repository import GroupRepository
from server.apps.groups.logic.value_objects import PaginatedGroupsPayload

if TYPE_CHECKING:
    from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(frozen=True, slots=True)
class ListGroupsUseCase:
    """Return the groups visible to ``user`` ordered pinned-first."""

    _group_repo: GroupRepository
    _group_mapper: GroupMapper

    def __call__(
        self,
        user: User,
        search: str | None,
        page: int,
        per_page: int,
    ) -> PaginatedGroupsPayload:
        """Run the use case and return a paginated payload."""
        log.debug(
            'list_groups_called',
            user_id=str(user.id),
            search=search,
            page=page,
            per_page=per_page,
        )
        groups, total = self._group_repo.list_for_user(
            user=user,
            role=user.role,
            search=search,
            page=page,
            per_page=per_page,
        )
        results = [self._group_mapper.to_payload(group) for group in groups]
        log.debug(
            'list_groups_done',
            count=len(results),
            total=total,
        )
        return PaginatedGroupsPayload(
            results=results,
            total=total,
            page=page,
            per_page=per_page,
        )
