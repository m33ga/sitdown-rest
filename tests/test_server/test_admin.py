from http import HTTPStatus

import pytest
from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from django.conf import LazySettings
from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.admin.sites import all_sites
from django.db.models import Model
from django.test import Client
from django.urls import reverse

from server.apps.users.models import User


@pytest.fixture(autouse=True)
def _strip_debug_toolbar_middleware(settings: LazySettings) -> None:
    """Drop django-debug-toolbar middleware for admin tests.

    The container's ``DJANGO_ENV=development`` makes pytest load
    development settings, which include ``DebugToolbarMiddleware``.
    With unfold's templates rendering full pages, the middleware tries
    to inject the toolbar and reverses ``djdt:...`` URLs that are NOT
    registered when ``DEBUG=False``. Stripping the middleware here
    keeps the admin tests environment-agnostic.
    """
    settings.MIDDLEWARE = tuple(
        middleware for middleware in settings.MIDDLEWARE
        if 'debug_toolbar' not in middleware
    )

# Models that should have restricted (FORBIDDEN) admin add pages
_RESTRICTED_ADMIN_ADD_MODELS = frozenset((
    AccessAttempt,
    AccessLog,
    AccessFailureLog,
))

# Creates a list of tuples containing all registered admin sites,
# their associated models, and corresponding model admin classes
# from the admin site's registry.
_MODEL_ADMIN_PARAMS = tuple(
    (site, model, model_admin)
    for site in all_sites
    for model, model_admin in site._registry.items()  # noqa: SLF001
)


def _make_url(site: AdminSite, model: type[Model], page: str) -> str:
    """Generates a URL for the given admin site, model, and page."""
    app_label = model._meta.app_label  # noqa: SLF001
    model_name = model._meta.model_name  # noqa: SLF001
    return reverse(f'{site.name}:{app_label}_{model_name}_{page}')  # noqa: WPS221


@pytest.mark.django_db
@pytest.mark.ignore_template_errors
@pytest.mark.parametrize(
    ('site', 'model', 'model_admin'),
    _MODEL_ADMIN_PARAMS,
)
def test_admin_changelist(
    admin_client: Client,
    site: AdminSite,
    model: type[Model],
    model_admin: type[ModelAdmin[Model]],
) -> None:
    """Ensures that admin changelist pages are accessible.

    ``ignore_template_errors`` is required because django-unfold's
    templates use a `{% capture as is_fullwidth %}` pattern that
    references the captured variable inside its own block, which
    pytest-django's ``--fail-on-template-vars`` flags as undefined.
    """
    url = _make_url(site, model, 'changelist')
    response = admin_client.get(url, {'q': 'something'})

    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
@pytest.mark.ignore_template_errors
@pytest.mark.parametrize(
    ('site', 'model', 'model_admin'),
    _MODEL_ADMIN_PARAMS,
)
def test_admin_add(
    admin_client: Client,
    site: AdminSite,
    model: type[Model],
    model_admin: type[ModelAdmin[Model]],
) -> None:
    """Ensures that admin add pages are accessible or restricted."""
    url = _make_url(site, model, 'add')
    response = admin_client.get(url)
    expected_status = (
        HTTPStatus.FORBIDDEN
        if model in _RESTRICTED_ADMIN_ADD_MODELS
        else HTTPStatus.OK
    )

    assert response.status_code == expected_status


@pytest.mark.django_db
@pytest.mark.ignore_template_errors
def test_admin_user_add_hashes_password(admin_client: Client) -> None:
    """Submitting the user-add form persists the password as an Argon2 hash.

    Pins the contract that ``UserAdmin`` keeps Django's ``UserCreationForm``
    flow (which calls ``set_password``) intact under the unfold theme.
    """
    plaintext = 'fresh-secret-90210'  # noqa: S105
    # ``follow=False`` avoids the admin redirect's user lookup which
    # zeal flags as an N+1 pattern in development-mode test runs.
    response = admin_client.post(
        reverse('admin:users_user_add'),
        {
            'username': 'admin-created',
            'password1': plaintext,
            'password2': plaintext,
            'role': 'MEMBER',
        },
    )

    assert response.status_code == HTTPStatus.FOUND  # admin redirects on success
    created = User.objects.get(username='admin-created')
    # The stored value MUST NOT equal the plaintext; ``check_password``
    # must verify it; and the value must look like a Django password
    # hash (algorithm prefix + ``$``). Tests use the fast MD5 hasher,
    # production uses argon2 — assert on the format, not the algorithm.
    assert created.password != plaintext
    assert created.check_password(plaintext)
    assert '$' in created.password
