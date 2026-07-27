#!/usr/bin/env python3
"""
Credential resolution for Onskeskyen/GoWish.

Supports, in order of precedence:
  1. Explicitly provided username/password.
  2. macOS Keychain via the `keyring` package (service=Onskeskyen).
  3. Environment variables ONSKESKYEN_USERNAME / ONSKESKYEN_PASSWORD
     (loaded from .env if present).
"""

import os
from typing import Optional, Tuple

from dotenv import load_dotenv
from loguru import logger

try:
    import keyring
except Exception:  # pragma: no cover - defensive import handling
    keyring = None  # type: ignore[assignment]


SERVICE_NAME = "Onskeskyen"
USERNAME_KEY = "__username__"


class CredentialsError(Exception):
    """Raised when credentials cannot be resolved."""


def load_env_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Load credentials from environment variables, loading .env first."""
    load_dotenv()
    username = os.getenv("ONSKESKYEN_USERNAME")
    password = os.getenv("ONSKESKYEN_PASSWORD")
    return username, password


def get_keychain_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Load credentials from the system keychain."""
    if keyring is None:
        logger.debug("keyring package not available; skipping keychain lookup")
        return None, None

    try:
        username = keyring.get_password(SERVICE_NAME, USERNAME_KEY)
        if not username:
            return None, None

        password = keyring.get_password(SERVICE_NAME, username)
        if not password:
            return username, None

        logger.debug(f"Loaded credentials for {username} from keychain")
        return username, password
    except Exception as exc:
        logger.warning(f"Failed to read credentials from keychain: {exc}")
        return None, None


def get_credentials(
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Resolve Onskeskyen credentials.

    Precedence:
      1. Explicit username/password arguments.
      2. macOS Keychain (if keyring is installed and a login has been stored).
      3. Environment variables ONSKESKYEN_USERNAME / ONSKESKYEN_PASSWORD.

    Raises CredentialsError if no complete set can be found.
    """
    if username and password:
        return username, password

    if username and not password:
        # Username supplied explicitly; try keychain for the password.
        if keyring is not None:
            try:
                stored_password = keyring.get_password(SERVICE_NAME, username)
                if stored_password:
                    return username, stored_password
            except Exception as exc:
                logger.warning(f"Failed to read password from keychain: {exc}")
        # Fall back to env for the password.
        _, env_password = load_env_credentials()
        if env_password:
            return username, env_password
        raise CredentialsError(
            "A username was provided but no password could be found "
            "in the keychain or environment variables."
        )

    # No explicit username; try keychain first, then env.
    keychain_username, keychain_password = get_keychain_credentials()
    if keychain_username and keychain_password:
        return keychain_username, keychain_password

    env_username, env_password = load_env_credentials()
    if env_username and env_password:
        return env_username, env_password

    raise CredentialsError(
        "No Onskeskyen credentials found.\n"
        "Run `oenskeskyen login` to store them in your keychain, "
        "or set ONSKESKYEN_USERNAME and ONSKESKYEN_PASSWORD in your environment."
    )


def store_credentials(username: str, password: str) -> None:
    """Persist credentials to the system keychain."""
    if keyring is None:
        raise CredentialsError(
            "The keyring package is not available; cannot store credentials."
        )

    try:
        keyring.set_password(SERVICE_NAME, USERNAME_KEY, username)
        keyring.set_password(SERVICE_NAME, username, password)
        logger.info(f"Credentials for {username} stored in keychain")
    except Exception as exc:
        raise CredentialsError(
            f"Failed to store credentials in keychain: {exc}"
        ) from exc


def delete_credentials() -> bool:
    """
    Delete stored credentials from the keychain.

    Returns True if credentials were deleted, False if none were stored.
    """
    if keyring is None:
        raise CredentialsError(
            "The keyring package is not available; cannot delete credentials."
        )

    username = keyring.get_password(SERVICE_NAME, USERNAME_KEY)
    if not username:
        return False

    try:
        keyring.delete_password(SERVICE_NAME, username)
    except Exception:
        pass

    try:
        keyring.delete_password(SERVICE_NAME, USERNAME_KEY)
    except Exception:
        pass

    logger.info(f"Credentials for {username} removed from keychain")
    return True
