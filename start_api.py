#!/usr/bin/env python3
"""
Startup script for the Onskeskyen API Gateway
Handles environment validation and server startup
"""

import os
import sys

import uvicorn
from loguru import logger

from src.credentials import CredentialsError, get_credentials


def validate_credentials():
    """Validate that credentials can be resolved."""
    try:
        get_credentials()
    except CredentialsError as exc:
        logger.error(str(exc))
        return False

    logger.success("✅ Credentials validated")
    return True


def main():
    """Main startup function"""
    logger.info("🚀 Starting Onskeskyen API Gateway...")

    if not validate_credentials():
        sys.exit(1)

    # Configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info")

    logger.info(f"📡 Server starting on http://{host}:{port}")
    logger.info(f"📖 API docs available at http://{host}:{port}/docs")
    logger.info(f"🔄 Reload mode: {'enabled' if reload else 'disabled'}")

    try:
        uvicorn.run(
            "app:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=True,
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
