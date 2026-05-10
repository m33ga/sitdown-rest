"""Unit tests for JWT use cases, repositories, and mapper (real DB, no mocking)."""

import uuid

import pytest

from server.apps.users.infra.mappers import UserMapper
from server.apps.users.infra.repository import RefreshTokenRepository, UserRepository
from server.apps.users.logic.exceptions import AuthenticationError, InvalidRefreshTokenError
from server.apps.users.logic.usecases.create_tokens import CreateTokensUseCase
from server.apps.users.logic.usecases.refresh_tokens import RefreshTokensUseCase
from server.apps.users.logic.value_objects import TokenCreatePayload, TokenRefreshPayload
from server.apps.users.models import User


def _make_user(username: str, password: str) -> User:
    return User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password=password,
    )


def _use_case() -> CreateTokensUseCase:
    return CreateTokensUseCase(
        user_repo=UserRepository(),
        refresh_token_repo=RefreshTokenRepository(),
    )


def _refresh_use_case() -> RefreshTokensUseCase:
    return RefreshTokensUseCase(
        user_repo=UserRepository(),
        refresh_token_repo=RefreshTokenRepository(),
    )


@pytest.mark.django_db
def test_create_tokens_use_case_returns_token_response() -> None:
    """CreateTokensUseCase returns TokenResponse with both tokens on valid credentials."""
    _make_user('uc_alice', 'password1')
    use_case = _use_case()
    result = use_case(TokenCreatePayload(username='uc_alice', password='password1'))
    assert result.access_token
    assert result.refresh_token


@pytest.mark.django_db
def test_create_tokens_use_case_raises_on_bad_credentials() -> None:
    """CreateTokensUseCase raises AuthenticationError on invalid password."""
    _make_user('uc_bob', 'correctpass')
    use_case = _use_case()
    with pytest.raises(AuthenticationError):
        use_case(TokenCreatePayload(username='uc_bob', password='wrongpass'))


@pytest.mark.django_db
def test_refresh_tokens_use_case_rotates_refresh_token() -> None:
    """RefreshTokensUseCase issues new tokens and revokes the old refresh token."""
    _make_user('uc_carol', 'password3')
    create_uc = _use_case()
    token_response = create_uc(TokenCreatePayload(username='uc_carol', password='password3'))
    old_refresh_token_id = token_response.refresh_token

    refresh_uc = _refresh_use_case()
    new_response = refresh_uc(TokenRefreshPayload(refresh_token=old_refresh_token_id))
    assert new_response.access_token
    assert new_response.refresh_token
    assert new_response.refresh_token != old_refresh_token_id

    with pytest.raises(InvalidRefreshTokenError):
        refresh_uc(TokenRefreshPayload(refresh_token=old_refresh_token_id))


@pytest.mark.django_db
def test_refresh_tokens_use_case_raises_on_invalid_token() -> None:
    """RefreshTokensUseCase raises InvalidRefreshTokenError for non-existent UUID."""
    refresh_uc = _refresh_use_case()
    with pytest.raises(InvalidRefreshTokenError):
        refresh_uc(TokenRefreshPayload(refresh_token=str(uuid.uuid4())))


@pytest.mark.django_db
def test_user_repository_get_by_id_not_found() -> None:
    """UserRepository.get_by_id returns None for an unknown UUID."""
    repo = UserRepository()
    result = repo.get_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.django_db
def test_user_mapper_to_payload() -> None:
    """UserMapper.to_payload maps User fields to UserPayload correctly."""
    user = _make_user('uc_mapper', 'mapperpass')
    mapper = UserMapper()
    payload = mapper.to_payload(user)
    assert payload.id == user.id
    assert payload.email == user.email
    assert payload.name == user.username
    assert payload.role == user.role
