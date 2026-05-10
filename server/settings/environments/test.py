"""Test environment: use in-memory SQLite so tests run without a Postgres server."""

SECRET_KEY = 'HTdAbOTxguNuCXhASPKl2sRAy0Bp1E0RZxMAlKUcHCJIDeGxJJ'  # noqa: S105

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
