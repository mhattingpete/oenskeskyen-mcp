import os
from unittest.mock import patch

import pytest

from src.credentials import (
    SERVICE_NAME,
    USERNAME_KEY,
    CredentialsError,
    delete_credentials,
    get_credentials,
    store_credentials,
)


@pytest.fixture(autouse=True)
def patch_load_dotenv():
    """Prevent .env files from influencing credential resolution during tests."""
    with patch("src.credentials.load_dotenv", lambda: None):
        yield


@pytest.fixture
def clear_env():
    """Remove ONSKESKYEN_* env vars before each test."""
    original = {
        "ONSKESKYEN_USERNAME": os.environ.get("ONSKESKYEN_USERNAME"),
        "ONSKESKYEN_PASSWORD": os.environ.get("ONSKESKYEN_PASSWORD"),
    }
    os.environ.pop("ONSKESKYEN_USERNAME", None)
    os.environ.pop("ONSKESKYEN_PASSWORD", None)
    yield
    for key, value in original.items():
        if value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)


@pytest.fixture
def mock_keyring(clear_env):
    """Replace keyring with a simple in-memory dict backend."""
    store: dict[tuple[str, str], str] = {}

    def get_password(service: str, username: str):
        return store.get((service, username))

    def set_password(service: str, username: str, password: str):
        store[(service, username)] = password

    def delete_password(service: str, username: str):
        store.pop((service, username), None)

    with patch(
        "src.credentials.keyring",
    ) as kr:
        kr.get_password = get_password
        kr.set_password = set_password
        kr.delete_password = delete_password
        yield store


def test_explicit_credentials_take_precedence(mock_keyring):
    # Even with empty keychain/env, explicit args win.
    assert get_credentials("explicit@example.com", "hunter2") == (
        "explicit@example.com",
        "hunter2",
    )


def test_keychain_credentials(mock_keyring):
    store_credentials("keychain@example.com", "secret123")
    assert get_credentials() == ("keychain@example.com", "secret123")
    assert mock_keyring[(SERVICE_NAME, USERNAME_KEY)] == "keychain@example.com"
    assert mock_keyring[(SERVICE_NAME, "keychain@example.com")] == "secret123"


def test_env_fallback_when_keychain_empty(mock_keyring):
    os.environ["ONSKESKYEN_USERNAME"] = "env@example.com"
    os.environ["ONSKESKYEN_PASSWORD"] = "envpass"
    assert get_credentials() == ("env@example.com", "envpass")


def test_keychain_takes_precedence_over_env(mock_keyring):
    os.environ["ONSKESKYEN_USERNAME"] = "env@example.com"
    os.environ["ONSKESKYEN_PASSWORD"] = "envpass"
    store_credentials("keychain@example.com", "secret123")
    assert get_credentials() == ("keychain@example.com", "secret123")


def test_explicit_username_with_env_password(mock_keyring):
    os.environ["ONSKESKYEN_USERNAME"] = "env@example.com"
    os.environ["ONSKESKYEN_PASSWORD"] = "envpass"
    assert get_credentials("explicit@example.com") == (
        "explicit@example.com",
        "envpass",
    )


def test_explicit_username_with_keychain_password(mock_keyring):
    store_credentials("explicit@example.com", "keychainpass")
    assert get_credentials("explicit@example.com") == (
        "explicit@example.com",
        "keychainpass",
    )


def test_missing_credentials_raises(mock_keyring):
    with pytest.raises(CredentialsError):
        get_credentials()


def test_explicit_username_missing_password_raises(mock_keyring):
    with pytest.raises(CredentialsError):
        get_credentials("explicit@example.com")


def test_delete_credentials(mock_keyring, clear_env):
    os.environ["ONSKESKYEN_USERNAME"] = "env@example.com"
    os.environ["ONSKESKYEN_PASSWORD"] = "envpass"
    store_credentials("delete@example.com", "secret")
    assert delete_credentials() is True
    assert get_credentials() == ("env@example.com", "envpass")


def test_delete_credentials_when_none_stored(mock_keyring, clear_env):
    assert delete_credentials() is False


def test_keychain_password_only_without_username_missing(mock_keyring):
    # Only password stored, no username -> should not find anything.
    mock_keyring[(SERVICE_NAME, "solo@example.com")] = "secret"
    with pytest.raises(CredentialsError):
        get_credentials()


def test_delete_credentials_cleans_username_and_password(mock_keyring):
    store_credentials("cleanup@example.com", "secret")
    assert delete_credentials() is True
    with pytest.raises(CredentialsError):
        get_credentials()
