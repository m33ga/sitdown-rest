import attrs
import structlog

from server.apps.users.logic.value_objects import UserPayload
from server.apps.users.models import User

log = structlog.get_logger()


@attrs.define(slots=True, frozen=True)
class UserMapper:
    def to_payload(self, user: User) -> UserPayload:
        log.debug('user_mapper_to_payload_called', user_id=str(user.id))
        return UserPayload(
            id=user.id,
            email=user.email,
            name=user.get_full_name() or user.username,
            role=user.role,
        )
