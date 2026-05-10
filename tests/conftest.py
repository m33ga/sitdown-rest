"""
This module is used to provide configuration, fixtures, and plugins for pytest.

It may be also used for extending doctest's context:
1. https://docs.python.org/3/library/doctest.html
2. https://docs.pytest.org/en/latest/doctest.html
"""

import os

# Force the test environment before Django is configured by pytest-django.
os.environ['DJANGO_ENV'] = 'test'

pytest_plugins = [
    # Should be the first custom one:
    'plugins.django_settings',
]
