# NOTE: simple layers go on top!

from collections.abc import Callable
from typing import Any

import punq


def _global_namespace() -> dict[str, Any]:  # pragma: no cover
    from django.conf import LazySettings  # noqa: F401
    from django.core.cache import BaseCache  # noqa: F401

    return locals()  # noqa: WPS421


def _create_injector[Thing](  # pragma: no cover
    container: punq.Container,
    localns: dict[str, Any],
) -> Callable[[Thing], Thing]:
    # We need to provide the same string names as we do in the definition.
    localns.pop('container')
    localns.update(_global_namespace())
    container.registrations._localns.update(localns)  # noqa: SLF001
    return lambda service: service


def _inject_django(container: punq.Container) -> None:
    from django.conf import LazySettings, settings

    # Django:
    container.register(
        LazySettings,
        instance=settings,
        scope=punq.Scope.singleton,
    )


def _inject_users(container: punq.Container) -> None:
    # Token issuance and refresh now use dmr's pre-built controllers
    # (ObtainTokensSyncController / RefreshTokenSyncController) which do
    # not go through punq DI. The Users domain has no use cases requiring
    # registration at this stage; this hook is left in place for future
    # additions (e.g. the Users directory milestone).
    pass


def _inject_groups(container: punq.Container) -> None:
    # See note in _inject_users: repos/mappers must be registered before
    # any use case that consumes them.
    from server.apps.groups.infra.mappers import (
        GroupMapper,
        ProjectMemberMapper,
    )
    from server.apps.groups.infra.repository import GroupRepository
    from server.apps.groups.logic.usecases.add_member import AddMemberUseCase
    from server.apps.groups.logic.usecases.create_group import (
        CreateGroupUseCase,
    )
    from server.apps.groups.logic.usecases.delete_group import (
        DeleteGroupUseCase,
    )
    from server.apps.groups.logic.usecases.list_groups import ListGroupsUseCase
    from server.apps.groups.logic.usecases.list_members import (
        ListMembersUseCase,
    )
    from server.apps.groups.logic.usecases.pin_group import PinGroupUseCase
    from server.apps.groups.logic.usecases.remove_member import (
        RemoveMemberUseCase,
    )
    from server.apps.groups.logic.usecases.unpin_group import UnpinGroupUseCase
    from server.apps.groups.logic.usecases.update_group import (
        UpdateGroupUseCase,
    )

    container.register(GroupRepository, scope=punq.Scope.singleton)
    container.register(GroupMapper, scope=punq.Scope.singleton)
    container.register(ProjectMemberMapper, scope=punq.Scope.singleton)
    container.register(ListGroupsUseCase)
    container.register(CreateGroupUseCase)
    container.register(UpdateGroupUseCase)
    container.register(DeleteGroupUseCase)
    container.register(PinGroupUseCase)
    container.register(UnpinGroupUseCase)
    container.register(ListMembersUseCase)
    container.register(AddMemberUseCase)
    container.register(RemoveMemberUseCase)


def _inject_meetings(container: punq.Container) -> None:
    pass  # Populated in: Meetings milestone


def populate_dependencies(container: punq.Container) -> punq.Container:
    """Populates dependencies for the container."""
    # Deps:
    _inject_django(container)
    # Apps:
    _inject_users(container)
    _inject_groups(container)
    _inject_meetings(container)
    return container
