import tomllib
from typing import Any, cast

from dmr.openapi import OpenAPIConfig
from dmr.openapi.objects import Tag
from dmr.security.jwt.auth import JWTSyncAuth
from dmr.settings import Settings

from server.settings.components import BASE_DIR, config


def _get_project_meta() -> dict[str, str]:  # lying about return type
    pyproject = BASE_DIR / 'pyproject.toml'
    return cast(
        dict[str, str],
        tomllib.loads(pyproject.read_text())['project'],
    )


# django-modern-rest
# https://django-modern-rest.readthedocs.io

DMR_SETTINGS: Any = {
    # Default OpenAPI config:
    Settings.openapi_config: OpenAPIConfig(
        title='sitdown-rest',
        version=_get_project_meta()['version'],
        tags=[
            Tag(name='auth', description='Token issuance'),
            Tag(name='groups', description='Project group management'),
            Tag(name='members', description='Project membership'),
            Tag(name='meetings', description='Standup meeting events'),
            Tag(
                name='entries',
                description='Per-member standup tabs inside a meeting',
            ),
            Tag(name='users', description='Organisation user directory'),
        ],
    ),
    # Generate fake examples in OpenAPI:
    Settings.openapi_examples_seed: 1,
    # Global JWT auth: every endpoint requires a valid Bearer token unless
    # the endpoint or controller explicitly sets `auth=None` (e.g. the
    # token-issuance and token-refresh endpoints).
    Settings.auth: [JWTSyncAuth()],
}


# django-cors-headers
# https://github.com/adamchainz/django-cors-headers

CORS_ALLOWED_ORIGINS = [
    f'https://{config("DOMAIN_NAME")}',
]
CORS_ALLOW_ALL_ORIGINS = False
