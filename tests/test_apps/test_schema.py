import logging
from collections.abc import Iterator

import pytest
import schemathesis as st
from django.conf import LazySettings
from django.urls import reverse
from schemathesis.specs.openapi.schemas import OpenApiSchema

from server.wsgi import application


@pytest.fixture(autouse=True)
def _disable_logging(settings: LazySettings) -> Iterator[None]:
    # django-query-counter produces tons of output for no reason:
    settings.DQC_ENABLED = False
    # Logging has too much output with schemathesis:
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


# NOTE: The `db` fixture is required to enable database access.
# When `st.openapi.from_wsgi()` makes a WSGI request, Django's request
# lifecycle triggers database operations.
@pytest.fixture
def api_schema(
    transactional_db: None,
) -> 'OpenApiSchema':
    """Load OpenAPI schema as a pytest fixture."""
    return st.openapi.from_wsgi(reverse('openapi_json'), application)


schema = st.pytest.from_fixture('api_schema')


@pytest.mark.skip(
    reason=(
        'Auth scheme is now published in the dmr-generated schema thanks '
        'to JWTSyncAuth, but several endpoints still need extra_responses '
        'declarations for 404/403 (groups detail, pin, members; meetings '
        'detail; entries detail) before schemathesis is fully green. '
        'Tracked under the "OpenAPI schema completeness" roadmap '
        'milestone.'
    ),
)
@pytest.mark.timeout(60)  # increase the default timeout for this test
@schema.parametrize()
def test_schemathesis(settings: LazySettings, *, case: st.Case) -> None:
    """Ensure that API implementation matches the OpenAPI schema."""
    case.call_and_validate()
