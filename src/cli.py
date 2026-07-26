#!/usr/bin/env python3
"""
Command-line interface for Onskeskyen batch upload and API operations.

Provides subcommands for login, wishlist CRUD, batch uploads, and running
supporting servers (FastAPI and MCP), using credentials stored in the macOS
keychain or environment variables.
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
import uvicorn
from loguru import logger

from src.auth_service import AuthenticationService
from src.credentials import (
    CredentialsError,
    delete_credentials,
    get_credentials,
    store_credentials,
)

app = typer.Typer(
    help="Onskeskyen CLI: manage your wishlists from the terminal.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Global state that callback commands can populate.
_global_username: Optional[str] = None
_global_password: Optional[str] = None
_output_json: bool = False


@app.callback()
def main(
    ctx: typer.Context,
    username: Optional[str] = typer.Option(
        None, "--username", help="Onskeskyen email (overrides keychain/env)."
    ),
    password: Optional[str] = typer.Option(
        None, "--password", help="Onskeskyen password (overrides keychain/env)."
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Print machine-readable JSON output."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging."
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-error output."
    ),
) -> None:
    """Onskeskyen CLI global options."""
    global _global_username, _global_password, _output_json
    _global_username = username
    _global_password = password
    _output_json = json_output

    if quiet:
        logger.remove()
        logger.add(sys.stderr, level="ERROR")
    elif verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")


@asynccontextmanager
async def get_auth_service():
    """Resolve credentials and yield an authenticated service."""
    username, password = get_credentials(_global_username, _global_password)
    service = AuthenticationService(username, password)
    await service.authenticate()
    logger.info(f"Authenticated as {username}")
    try:
        yield service
    finally:
        await service._cleanup()


def _render(data: Any) -> str:
    """Render output as JSON if requested, otherwise pretty-print."""
    if _output_json:
        return json.dumps(data, default=str, indent=2, ensure_ascii=False)
    return _pretty(data)


def _pretty(data: Any, indent: int = 0) -> str:
    """Minimal pretty printer for human-readable output."""
    prefix = "  " * indent
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if value is None or value == []:
                continue
            rendered = _pretty(value, indent + 1)
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(rendered)
            else:
                lines.append(f"{prefix}{key}: {rendered}")
        return "\n".join(lines) if lines else f"{prefix}(empty)"
    if isinstance(data, list):
        if not data:
            return f"{prefix}(empty)"
        lines = []
        for i, item in enumerate(data, 1):
            rendered = _pretty(item, indent + 1)
            lines.append(f"{prefix}[{i}]\n{rendered}")
        return "\n".join(lines)
    return str(data)


def _exit_with_error(message: str) -> None:
    """Print a user-friendly error and exit."""
    logger.error(message)
    raise typer.Exit(1)


@app.command()
def login(
    username: Optional[str] = typer.Option(
        None, "--username", "-u", help="Email to store in the keychain."
    ),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        "-p",
        help="Password to store in the keychain.",
        hide_input=True,
    ),
) -> None:
    """Store Onskeskyen credentials in the system keychain."""
    if not username:
        username = typer.prompt("Email")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    assert username is not None and password is not None

    try:
        store_credentials(username, password)
    except CredentialsError as exc:
        _exit_with_error(str(exc))

    if _output_json:
        print(json.dumps({"status": "ok", "username": username}))
    else:
        print(f"Credentials for {username} stored in keychain.")


@app.command()
def logout(
    force: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Remove stored Onskeskyen credentials from the keychain."""
    if not force:
        confirmed = typer.confirm("Delete stored Onskeskyen credentials?")
        if not confirmed:
            raise typer.Abort()

    deleted = False
    try:
        deleted = delete_credentials()
    except CredentialsError as exc:
        _exit_with_error(str(exc))

    if _output_json:
        print(json.dumps({"status": "ok", "deleted": deleted}))
    else:
        if deleted:
            print("Credentials removed from keychain.")
        else:
            print("No stored credentials found.")


async def _whoami() -> None:
    async with get_auth_service() as auth:
        data = await auth.get_me()
        me = data.get("data", {}).get("me", {}) if isinstance(data, dict) else {}
        profile = {
            "id": me.get("id"),
            "email": me.get("email"),
            "first_name": me.get("firstName"),
            "last_name": me.get("lastName"),
            "language_code": me.get("languageCode"),
            "country_code": me.get("countryCode"),
            "profile_image": me.get("profileImage"),
        }
        print(_render(profile))


@app.command()
def whoami() -> None:
    """Show the currently authenticated user profile."""
    asyncio.run(_whoami())


async def _wishlists(limit: int, cursor: int) -> None:
    async with get_auth_service() as auth:
        data = await auth.get_wishlists_paginated(limit=limit, cursor=cursor)
        wishlists = []
        if isinstance(data, dict) and data.get("data", {}).get("wishlists"):
            wishlists = data["data"]["wishlists"].get("data", [])
        print(_render(wishlists))


@app.command()
def wishlists(
    limit: int = typer.Option(50, "--limit", "-l", min=1, max=100),
    cursor: int = typer.Option(0, "--cursor", "-c", min=0),
) -> None:
    """List your wishlists."""
    asyncio.run(_wishlists(limit=limit, cursor=cursor))


async def _wishlist(wishlist_id: str) -> None:
    async with get_auth_service() as auth:
        data = await auth.get_wishlist_page(wishlist_id)
        wishlist = {}
        if isinstance(data, dict) and data.get("data", {}).get("wishlist"):
            wishlist = data["data"]["wishlist"]
        print(_render(wishlist))


@app.command()
def wishlist(wishlist_id: str = typer.Argument(..., help="Wishlist ID")) -> None:
    """Show details for a specific wishlist."""
    asyncio.run(_wishlist(wishlist_id))


async def _items(wishlist_id: str, limit: int, cursor: int) -> None:
    async with get_auth_service() as auth:
        data = await auth.get_wishlist_wishes(
            wishlist_id=wishlist_id, limit=limit, cursor=cursor
        )
        items = []
        if isinstance(data, dict) and data.get("data", {}).get("wishlist", {}).get(
            "wishes"
        ):
            items = data["data"]["wishlist"]["wishes"].get("data", [])
        print(_render(items))


@app.command()
def items(
    wishlist_id: str = typer.Argument(..., help="Wishlist ID"),
    limit: int = typer.Option(24, "--limit", "-l", min=1, max=100),
    cursor: int = typer.Option(0, "--cursor", "-c", min=0),
) -> None:
    """List items in a wishlist."""
    asyncio.run(_items(wishlist_id=wishlist_id, limit=limit, cursor=cursor))


async def _add(
    wishlist_id: str,
    url: str,
    title: Optional[str],
    description: Optional[str],
    price: Optional[float],
    quantity: int,
    use_url_metadata: bool,
) -> None:
    async with get_auth_service() as auth:
        result = await auth.create_wish(
            wishlist_id=wishlist_id,
            url=url,
            title=title,
            description=description,
            price=price,
            quantity=quantity,
            use_url_metadata=use_url_metadata,
        )

        wish_data = {}
        if isinstance(result, dict) and result.get("data", {}).get("wish", {}).get(
            "create"
        ):
            wish_data = result["data"]["wish"]["create"]

        print(_render({"success": True, "wish": wish_data}))


@app.command()
def add(
    wishlist_id: str = typer.Option(..., "--wishlist-id", "-w", help="Wishlist ID"),
    url: str = typer.Option(..., "--url", "-u", help="Product URL to add"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Custom title"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Custom description"
    ),
    price: Optional[float] = typer.Option(None, "--price", "-p", help="Custom price"),
    quantity: int = typer.Option(1, "--quantity", "-q", min=1, max=100),
    use_url_metadata: bool = typer.Option(
        True, "--use-url-metadata/--no-url-metadata", help="Fetch metadata from URL"
    ),
) -> None:
    """Add a product URL to a wishlist."""
    asyncio.run(
        _add(
            wishlist_id=wishlist_id,
            url=url,
            title=title,
            description=description,
            price=price,
            quantity=quantity,
            use_url_metadata=use_url_metadata,
        )
    )


async def _product(url: str, country_code: str) -> None:
    async with get_auth_service() as auth:
        result = await auth.get_product_by_url(url, country_code)
        product = {}
        if isinstance(result, dict) and result.get("data", {}).get("products", {}).get(
            "getByUrlV2"
        ):
            product = result["data"]["products"]["getByUrlV2"]
        print(_render({"success": bool(product), "product": product}))


@app.command()
def product(
    url: str = typer.Option(..., "--url", "-u", help="Product URL"),
    country_code: str = typer.Option(
        "DK", "--country-code", "-c", help="Country code for metadata lookup"
    ),
) -> None:
    """Fetch product metadata for a URL."""
    asyncio.run(_product(url=url, country_code=country_code))


def _extract_urls(content: str, lego_only: bool = True) -> List[str]:
    """Extract URLs from wishes.txt content."""
    urls: List[str] = []
    for line in content.splitlines():
        if lego_only and "https://www.lego.com/" not in line:
            continue

        start = line.find("https://")
        if start == -1:
            continue

        # Keep the same lego-specific extraction used in main.py, but generalise
        # to any https:// URL if --all-urls is passed.
        if lego_only:
            start = line.find("https://www.lego.com/")
            if start == -1:
                continue

        end = line.find('"', start)
        if end == -1:
            end = len(line)
        url = line[start:end].strip()
        if url:
            urls.append(url)
    return urls


async def _batch(
    file: Path,
    wishlist_id: str,
    lego_only: bool,
    dry_run: bool,
) -> None:
    if not file.exists():
        _exit_with_error(f"File not found: {file}")

    content = file.read_text()
    urls = _extract_urls(content, lego_only=lego_only)
    if not urls:
        _exit_with_error("No URLs found in file.")

    logger.info(f"Found {len(urls)} URL(s) to add to wishlist {wishlist_id}")

    if dry_run:
        print(_render({"dry_run": True, "wishlist_id": wishlist_id, "urls": urls}))
        return

    async with get_auth_service() as auth:
        results: List[Dict[str, Any]] = []
        for i, url in enumerate(urls, 1):
            try:
                result = await auth.create_wish(
                    wishlist_id=wishlist_id,
                    url=url,
                    quantity=1,
                    use_url_metadata=True,
                )
                wish_data = {}
                if isinstance(result, dict) and result.get("data", {}).get(
                    "wish", {}
                ).get("create"):
                    wish_data = result["data"]["wish"]["create"]
                results.append({"url": url, "status": "ok", "wish": wish_data})
                logger.info(f"[{i}/{len(urls)}] Added {url}")
            except Exception as exc:
                logger.error(f"[{i}/{len(urls)}] Failed to add {url}: {exc}")
                results.append({"url": url, "status": "error", "error": str(exc)})

        summary = {
            "total": len(urls),
            "success": sum(1 for r in results if r["status"] == "ok"),
            "failed": sum(1 for r in results if r["status"] == "error"),
            "results": results,
        }
        print(_render(summary))


@app.command()
def batch(
    file: Path = typer.Option(
        Path("wishes.txt"), "--file", "-f", help="Path to file containing URLs"
    ),
    wishlist_id: str = typer.Option(
        ..., "--wishlist-id", "-w", help="Wishlist ID to add items to"
    ),
    lego_only: bool = typer.Option(
        True,
        "--lego-only/--all-urls",
        help="Only add LEGO URLs (matches legacy main.py behavior)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print URLs without adding them"
    ),
) -> None:
    """Batch-add URLs from a file to a wishlist."""
    asyncio.run(
        _batch(file=file, wishlist_id=wishlist_id, lego_only=lego_only, dry_run=dry_run)
    )


@app.command()
def api(
    host: Optional[str] = typer.Option(None, "--host", "-H", help="Bind host"),
    port: Optional[int] = typer.Option(
        None, "--port", "-p", help="Bind port", min=1, max=65535
    ),
    reload: bool = typer.Option(
        False, "--reload/--no-reload", help="Enable auto-reload"
    ),
    log_level: str = typer.Option(
        "info", "--log-level", "-l", help="Uvicorn log level"
    ),
) -> None:
    """Start the Onskeskyen FastAPI server."""
    host = host or os.getenv("HOST", "0.0.0.0")
    port = port or int(os.getenv("PORT", "8000"))
    logger.info(f"Starting API server on http://{host}:{port}")
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True,
    )


@app.command()
def mcp() -> None:
    """Start the Onskeskyen MCP server."""
    from mcp_server import mcp as mcp_server

    logger.info("Starting MCP server")
    mcp_server.run()


if __name__ == "__main__":
    app()
