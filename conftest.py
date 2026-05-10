"""Root conftest — sets DJANGO_ENV before pytest-django initialises Django."""

import os

os.environ['DJANGO_ENV'] = 'test'
