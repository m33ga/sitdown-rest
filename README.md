# sitdown-rest

[![wemake.services](https://img.shields.io/badge/%20-wemake.services-green.svg?label=%20&logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAABGdBTUEAALGPC%2FxhBQAAAAFzUkdCAK7OHOkAAAAbUExURQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP%2F%2F%2F5TvxDIAAAAIdFJOUwAjRA8xXANAL%2Bv0SAAAADNJREFUGNNjYCAIOJjRBdBFWMkVQeGzcHAwksJnAPPZGOGAASzPzAEHEGVsLExQwE7YswCb7AFZSF3bbAAAAABJRU5ErkJggg%3D%3D)](https://wemake-services.github.io)
[![wemake-python-styleguide](https://img.shields.io/badge/style-wemake-000000.svg)](https://github.com/wemake-services/wemake-python-styleguide)
[![Modern REST](https://img.shields.io/badge/Modern%20REST-0C4B33?logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTA4MCIgaGVpZ2h0PSIxMDgwIiB2aWV3Qm94PSIwIDAgMTA4MCAxMDgwIiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8cGF0aCBkPSJNMiA3MDQuMDJMMTQ1LjQ1OSA0NjYuMTlMMjc3Ljg4MyA3MDQuMDJMMTQ1LjQ1OSA5NDEuODQ5TDIgNzA0LjAyWiIgZmlsbD0id2hpdGUiLz4KPHBhdGggZD0iTTE0NS40NTkgOTQxLjg0OUwyIDcwNC4wMkgyNzcuODgzTDE0NS40NTkgOTQxLjg0OVoiIGZpbGw9IndoaXRlIi8+CjxwYXRoIGQ9Ik02NzguOTQ4IDcwNC4wMzVMMzQxLjIzIDEzOEwyMjcuMDcxIDMyOC4yNjRMNDM2LjM2MiA3MDQuMDM1TDMwMy4xNzcgOTQxLjg2NEg1MzYuMjVMNjc4Ljk0OCA3MDQuMDM1WiIgZmlsbD0id2hpdGUiLz4KPHBhdGggZD0iTTY3OC45MzcgNzA0LjAyNkg0MzYuMzVMMzAzLjE2NiA5NDEuODU2SDUzNi4yMzlMNjc4LjkzNyA3MDQuMDI2WiIgZmlsbD0id2hpdGUiLz4KPHBhdGggZD0iTTEwNzguMTcgNzA0LjAzNUw3NDAuNDUxIDEzOEw2MjYuMjkzIDMyOC4yNjRMODM1LjU4MyA3MDQuMDM1TDcwMi4zOTkgOTQxLjg2NEg5MzUuNDcyTDEwNzguMTcgNzA0LjAzNVoiIGZpbGw9IndoaXRlIi8+CjxwYXRoIGQ9Ik0xMDc4LjE3IDcwNC4wMzVIODM1LjU4M0w3MDIuMzk5IDk0MS44NjRIOTM1LjQ3MkwxMDc4LjE3IDcwNC4wMzVaIiBmaWxsPSJ3aGl0ZSIvPgo8L3N2Zz4K&color=35544A)](https://github.com/wemake-services/django-modern-rest)

the server that tells you to sitdown and rest during your standup meeting. in a restful approach.

scaffolded from [`wemake-django-template`](https://github.com/wemake-services/wemake-django-template) (template version: [a1cbd80](https://github.com/wemake-services/wemake-django-template/tree/a1cbd804b923e51ac068b6e714bb170da5a0d767)), powered by [django-modern-rest](https://github.com/wemake-services/django-modern-rest).

## what it is

a tiny rest api for tracking standups across teams and projects. groups, meetings, member entries. nothing else.

## what it does

- multiple project groups, each with its own members
- per-member entries with five sections: promised -> done -> will do -> discussion -> notes
- new meeting auto-fills each member's `promised` from their last non-empty `will do` in that group
- adding a member to a group backfills entries for every open meeting (signal-driven, idempotent)
- role-aware: manager creates/edits everything, member edits their own row, guest just watches
- jwt bearer auth on every endpoint (except `/token` and `/token/refresh`, obviously)
- stoplight, swagger, scalar, redoc
- pair it with the [standup spa](https://m33ga.github.io/sitdown/) or curl your own way through it. you decide.

## stack

- python 3.13, django 6, [django-modern-rest](https://github.com/wemake-services/django-modern-rest)
- clean per-app layering (`api` -> `logic` -> `infra`) wired through punq dependency injection
- postgres + msgspec for fast (de)serialization
- structlog for logs, django-axes for brute-force lockout
- jwt access + refresh tokens, role claims folded into `extras`
- docker compose for local, caddy + gunicorn on a digital ocean droplet for prod
- github actions: ruff, pytest (100% coverage gate), import-linter, build -> push to ghcr -> ssh deploy
