import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.cli import app
from src.credentials import CredentialsError

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_keyring(monkeypatch):
    """Provide a clean, in-memory keyring backend and empty env for every CLI test."""
    store: dict[tuple[str, str], str] = {}
    monkeypatch.delenv("ONSKESKYEN_USERNAME", raising=False)
    monkeypatch.delenv("ONSKESKYEN_PASSWORD", raising=False)

    def get_password(service: str, username: str):
        return store.get((service, username))

    def set_password(service: str, username: str, password: str):
        store[(service, username)] = password

    def delete_password(service: str, username: str):
        store.pop((service, username), None)

    with patch("src.credentials.load_dotenv", lambda: None):
        with patch("src.credentials.keyring") as kr:
            kr.get_password = get_password
            kr.set_password = set_password
            kr.delete_password = delete_password
            yield store


def make_fake_auth_service():
    """Return a callable that yields a mock auth service for async with."""
    auth = MagicMock()
    auth.get_me = AsyncMock(
        return_value={
            "data": {
                "me": {
                    "id": "u1",
                    "email": "test@example.com",
                    "firstName": "T",
                    "lastName": "E",
                }
            }
        }
    )
    auth.get_wishlists_paginated = AsyncMock(
        return_value={
            "data": {"wishlists": {"data": [{"id": "wl1", "title": "Birthday"}]}}
        }
    )
    auth.get_wishlist_page = AsyncMock(
        return_value={"data": {"wishlist": {"id": "wl1", "title": "Birthday"}}}
    )
    auth.get_wishlist_wishes = AsyncMock(
        return_value={
            "data": {"wishlist": {"wishes": {"data": [{"id": "w1", "title": "Gift"}]}}}
        }
    )
    auth.create_wish = AsyncMock(
        return_value={"data": {"wish": {"create": {"id": "w2", "title": "New Gift"}}}}
    )
    auth.get_product_by_url = AsyncMock(
        return_value={"data": {"products": {"getByUrlV2": {"title": "Product"}}}}
    )

    @asynccontextmanager
    async def _fake_auth():
        yield auth

    return _fake_auth, auth


def test_login(mock_keyring):
    result = runner.invoke(
        app, ["login", "--username", "test@example.com", "--password", "secret"]
    )
    assert result.exit_code == 0, result.output
    assert "stored" in result.stdout.lower()
    assert mock_keyring[("Onskeskyen", "__username__")] == "test@example.com"


def test_login_json(mock_keyring):
    result = runner.invoke(
        app,
        ["--json", "login", "--username", "test@example.com", "--password", "secret"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["username"] == "test@example.com"


def test_logout_no_credentials(mock_keyring):
    result = runner.invoke(app, ["logout", "--yes"])
    assert result.exit_code == 0
    assert "No stored credentials" in result.stdout


def test_logout_deletes_credentials(mock_keyring):
    result = runner.invoke(
        app, ["login", "--username", "test@example.com", "--password", "secret"]
    )
    assert result.exit_code == 0

    result = runner.invoke(app, ["logout", "--yes"])
    assert result.exit_code == 0
    assert "removed" in result.stdout.lower()


def test_whoami(mock_keyring):
    with patch("src.credentials.keyring") as kr:
        kr.get_password = lambda service, username: {
            ("Onskeskyen", "__username__"): "test@example.com",
            ("Onskeskyen", "test@example.com"): "secret",
        }.get((service, username))

        fake_auth, _ = make_fake_auth_service()
        with patch("src.cli.get_auth_service", fake_auth):
            result = runner.invoke(app, ["whoami"])

    assert result.exit_code == 0, result.output
    assert "test@example.com" in result.stdout


def test_whoami_json(mock_keyring):
    with patch("src.credentials.keyring") as kr:
        kr.get_password = lambda service, username: {
            ("Onskeskyen", "__username__"): "test@example.com",
            ("Onskeskyen", "test@example.com"): "secret",
        }.get((service, username))

        fake_auth, _ = make_fake_auth_service()
        with patch("src.cli.get_auth_service", fake_auth):
            result = runner.invoke(app, ["--json", "whoami"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["email"] == "test@example.com"


def test_wishlists(mock_keyring):
    with patch("src.credentials.keyring") as kr:
        kr.get_password = lambda service, username: {
            ("Onskeskyen", "__username__"): "test@example.com",
            ("Onskeskyen", "test@example.com"): "secret",
        }.get((service, username))

        fake_auth, _ = make_fake_auth_service()
        with patch("src.cli.get_auth_service", fake_auth):
            result = runner.invoke(app, ["wishlists"])

    assert result.exit_code == 0, result.output
    assert "Birthday" in result.stdout


def test_items(mock_keyring):
    with patch("src.credentials.keyring") as kr:
        kr.get_password = lambda service, username: {
            ("Onskeskyen", "__username__"): "test@example.com",
            ("Onskeskyen", "test@example.com"): "secret",
        }.get((service, username))

        fake_auth, auth = make_fake_auth_service()
        with patch("src.cli.get_auth_service", fake_auth):
            result = runner.invoke(app, ["items", "wl1"])

    assert result.exit_code == 0, result.output
    assert "Gift" in result.stdout
    auth.get_wishlist_wishes.assert_awaited_once_with(
        wishlist_id="wl1", limit=24, cursor=0
    )


def test_add(mock_keyring):
    with patch("src.credentials.keyring") as kr:
        kr.get_password = lambda service, username: {
            ("Onskeskyen", "__username__"): "test@example.com",
            ("Onskeskyen", "test@example.com"): "secret",
        }.get((service, username))

        fake_auth, auth = make_fake_auth_service()
        with patch("src.cli.get_auth_service", fake_auth):
            result = runner.invoke(
                app,
                [
                    "add",
                    "--wishlist-id",
                    "wl1",
                    "--url",
                    "https://example.com/item",
                    "--title",
                    "Item",
                    "--description",
                    "Nice",
                    "--price",
                    "99.99",
                    "--quantity",
                    "2",
                    "--no-url-metadata",
                ],
            )

    assert result.exit_code == 0, result.output
    assert "New Gift" in result.stdout
    auth.create_wish.assert_awaited_once_with(
        wishlist_id="wl1",
        url="https://example.com/item",
        title="Item",
        description="Nice",
        price=99.99,
        quantity=2,
        use_url_metadata=False,
    )


def test_product(mock_keyring):
    with patch("src.credentials.keyring") as kr:
        kr.get_password = lambda service, username: {
            ("Onskeskyen", "__username__"): "test@example.com",
            ("Onskeskyen", "test@example.com"): "secret",
        }.get((service, username))

        fake_auth, auth = make_fake_auth_service()
        with patch("src.cli.get_auth_service", fake_auth):
            result = runner.invoke(
                app,
                [
                    "product",
                    "--url",
                    "https://example.com/item",
                    "--country-code",
                    "US",
                ],
            )

    assert result.exit_code == 0, result.output
    assert "Product" in result.stdout
    auth.get_product_by_url.assert_awaited_once_with("https://example.com/item", "US")


def test_batch(mock_keyring, tmp_path):
    wish_file = tmp_path / "wishes.txt"
    wish_file.write_text(
        'Some LEGO item <a href="https://www.lego.com/da-dk/product/123">link</a>'
    )

    with patch("src.credentials.keyring") as kr:
        kr.get_password = lambda service, username: {
            ("Onskeskyen", "__username__"): "test@example.com",
            ("Onskeskyen", "test@example.com"): "secret",
        }.get((service, username))

        fake_auth, auth = make_fake_auth_service()
        with patch("src.cli.get_auth_service", fake_auth):
            result = runner.invoke(
                app, ["batch", "--wishlist-id", "wl1", "--file", str(wish_file)]
            )

    assert result.exit_code == 0, result.output
    assert "success" in result.stdout.lower()
    auth.create_wish.assert_awaited_once()


def test_batch_dry_run(mock_keyring, tmp_path):
    wish_file = tmp_path / "wishes.txt"
    wish_file.write_text(
        'Some LEGO item <a href="https://www.lego.com/da-dk/product/456">link</a>'
    )

    with patch("src.credentials.keyring") as kr:
        kr.get_password = lambda service, username: {
            ("Onskeskyen", "__username__"): "test@example.com",
            ("Onskeskyen", "test@example.com"): "secret",
        }.get((service, username))

        fake_auth, auth = make_fake_auth_service()
        with patch("src.cli.get_auth_service", fake_auth):
            result = runner.invoke(
                app,
                [
                    "batch",
                    "--wishlist-id",
                    "wl1",
                    "--file",
                    str(wish_file),
                    "--dry-run",
                ],
            )

    assert result.exit_code == 0, result.output
    auth.create_wish.assert_not_awaited()
    assert "https://www.lego.com/da-dk/product/456" in result.stdout


def test_batch_all_urls(mock_keyring, tmp_path):
    wish_file = tmp_path / "wishes.txt"
    wish_file.write_text('Non-LEGO link <a href="https://example.com/other">other</a>')

    with patch("src.credentials.keyring") as kr:
        kr.get_password = lambda service, username: {
            ("Onskeskyen", "__username__"): "test@example.com",
            ("Onskeskyen", "test@example.com"): "secret",
        }.get((service, username))

        fake_auth, auth = make_fake_auth_service()
        with patch("src.cli.get_auth_service", fake_auth):
            result = runner.invoke(
                app,
                [
                    "batch",
                    "--wishlist-id",
                    "wl1",
                    "--file",
                    str(wish_file),
                    "--all-urls",
                ],
            )

    assert result.exit_code == 0, result.output
    auth.create_wish.assert_awaited_once()


def test_missing_credentials_exits_error(mock_keyring):
    # No keychain and no env -> command should fail with a helpful message.
    result = runner.invoke(app, ["whoami"])
    assert result.exit_code == 1
    assert result.exception is not None
    assert isinstance(result.exception, CredentialsError)
    assert "oenskeskyen login" in str(result.exception)


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "login" in result.stdout
    assert "batch" in result.stdout
