#!/usr/bin/env python3
"""
Legacy entry point for Onskeskyen batch upload.

This thin wrapper preserves the original `python main.py` behavior while
routing all logic through the Typer CLI. If the WISHLIST_ID environment
variable is set, `main.py` defaults to the `batch` command; otherwise it
forwards arguments to the CLI as usual.
"""

import os
import sys

from src.cli import app

CLI_COMMANDS = {
    "login",
    "logout",
    "whoami",
    "wishlists",
    "wishlist",
    "items",
    "add",
    "product",
    "batch",
    "api",
    "mcp",
}


if __name__ == "__main__":
    args = sys.argv[1:]
    wishlist_id = os.getenv("WISHLIST_ID")

    # If no CLI command is present and WISHLIST_ID is set, default to batch.
    if (not args or args[0] not in CLI_COMMANDS) and wishlist_id:
        app(["batch", "--wishlist-id", wishlist_id, *args])
    else:
        app()
