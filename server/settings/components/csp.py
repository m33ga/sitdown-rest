"""
This file contains a definition for Content-Security-Policy headers.

Read more about it:
https://developer.mozilla.org/ru/docs/Web/HTTP/Headers/Content-Security-Policy

We are using `django-csp` to provide these headers.
Docs: https://github.com/mozilla/django-csp
"""

from typing import TypedDict, final

from csp.constants import NONE, SELF


@final
class _ContentSecurityPolicy(TypedDict):
    EXCLUDE_URL_PREFIXES: list[str]  # noqa: WPS115
    DIRECTIVES: dict[str, list[str]]  # noqa: WPS115


# These values might and will be redefined in `development.py` env:
CONTENT_SECURITY_POLICY: _ContentSecurityPolicy = {
    'EXCLUDE_URL_PREFIXES': [
        '/docs/stoplight/',
        '/docs/swagger/',
        '/docs/scalar/',
        '/docs/redoc/',
        # django-unfold's admin UI relies on Alpine.js (needs ``unsafe-eval``
        # to evaluate ``x-data`` / ``x-bind`` / ``x-show`` expressions) and
        # inline styles applied at runtime by Alpine and htmx. The admin is
        # staff-authenticated and ships trusted bundled JS, so we exclude
        # the prefix from CSP enforcement rather than weakening the global
        # script-src / style-src directives. Without this, the modal
        # overlay's ``x-show="openModal"`` cannot evaluate and the panel
        # renders opaque on top of the login form.
        '/admin/',
    ],
    'DIRECTIVES': {
        'default-src': [NONE],
        'script-src': [SELF],
        'style-src': [SELF],
        'img-src': [SELF],
        'font-src': [SELF],
        'connect-src': [],
    },
}
