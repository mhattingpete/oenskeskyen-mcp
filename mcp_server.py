#!/usr/bin/env python3
"""
MCP Server for Onskeskyen API
Exposes existing FastAPI endpoints as MCP tools for LLM interaction
"""

import os
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from loguru import logger

from src.auth_service import AuthenticationService

# Load environment variables from .env file if it exists (for development)
# Production/Claude Desktop usage should rely on environment variables passed in config
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

# Initialize MCP server
mcp = FastMCP("Onskeskyen Wishlist API")

# Global authentication service
auth_service: Optional[AuthenticationService] = None


async def get_authenticated_service() -> AuthenticationService:
    """Get or initialize the authentication service"""
    global auth_service

    if auth_service is None or not auth_service.is_authenticated():
        username = os.getenv("ONSKESKYEN_USERNAME")
        password = os.getenv("ONSKESKYEN_PASSWORD")
        
        logger.info(f"[MCP AUTH] Environment check - Username: {repr(username)}, Password: {'***' if password else None}")

        if not username or not password:
            # Try loading .env again in case it wasn't loaded properly (only if .env exists)
            if os.path.exists('.env'):
                from dotenv import load_dotenv
                load_dotenv()
                username = os.getenv("ONSKESKYEN_USERNAME")
                password = os.getenv("ONSKESKYEN_PASSWORD")
                logger.info(f"[MCP AUTH] After .env reload - Username: {repr(username)}, Password: {'***' if password else None}")
            
            if not username or not password:
                raise ValueError(
                    "Missing ONSKESKYEN_USERNAME or ONSKESKYEN_PASSWORD environment variables. "
                    "These should be set in your Claude Desktop configuration or .env file."
                )

        auth_service = AuthenticationService(username, password)
        await auth_service.authenticate()
        logger.info("✅ Authentication successful")

    return auth_service


@mcp.tool()
async def get_user_profile() -> Dict[str, Any]:
    """Get the current user's profile information"""
    auth = await get_authenticated_service()
    user_data = await auth.get_me()
    return {
        "id": user_data.get("id"),
        "name": user_data.get("name"),
        "email": user_data.get("email"),
        "avatar_url": user_data.get("avatarUrl"),
        "username": user_data.get("username"),
    }


@mcp.tool()
async def get_wishlists(limit: int = 50, cursor: int = 0) -> List[Dict[str, Any]]:
    """
    Get all user wishlists with pagination

    Args:
        limit: Number of wishlists to return (1-100, default: 50)
        cursor: Pagination cursor (default: 0)
    """
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    if cursor < 0:
        raise ValueError("Cursor must be >= 0")

    auth = await get_authenticated_service()
    wishlists_data = await auth.get_wishlists_paginated(limit=limit, cursor=cursor)

    # Handle the GraphQL response structure
    if wishlists_data.get("data") and wishlists_data["data"].get("wishlists"):
        wishlists = wishlists_data["data"]["wishlists"].get("data", [])
    else:
        wishlists = []

    return [
        {
            "id": wl.get("id"),
            "title": wl.get("title"),
            "description": wl.get("description"),
            "created_at": wl.get("createdAt"),
            "updated_at": wl.get("updatedAt"),
            "total_wishes": wl.get("totalWishes", 0),
            "slug": wl.get("slug"),
            "visibility": wl.get("visibility"),
        }
        for wl in wishlists
    ]


@mcp.tool()
async def get_wishlist_items(
    wishlist_id: str, limit: int = 24, cursor: int = 0
) -> List[Dict[str, Any]]:
    """
    Get items from a specific wishlist

    Args:
        wishlist_id: The ID of the wishlist
        limit: Number of items to return (1-100, default: 24)
        cursor: Pagination cursor (default: 0)
    """
    if not wishlist_id:
        raise ValueError("Wishlist ID is required")
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    if cursor < 0:
        raise ValueError("Cursor must be >= 0")

    auth = await get_authenticated_service()
    items_data = await auth.get_wishlist_wishes(
        wishlist_id=wishlist_id, limit=limit, cursor=cursor
    )

    # Handle the GraphQL response structure
    if (
        items_data.get("data")
        and items_data["data"].get("wishlist")
        and items_data["data"]["wishlist"].get("wishes")
    ):
        wishes = items_data["data"]["wishlist"]["wishes"].get("data", [])
    else:
        wishes = []

    return [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "description": item.get("description"),
            "url": item.get("url"),
            "price": item.get("price"),
            "currency": item.get("currency"),
            "quantity": item.get("quantity"),
            "image_url": item.get("imageUrl"),
            "created_at": item.get("createdAt"),
            "updated_at": item.get("updatedAt"),
        }
        for item in wishes
    ]


@mcp.tool()
async def add_wishlist_item(
    wishlist_id: str,
    url: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[float] = None,
    quantity: int = 1,
    use_url_metadata: bool = True,
) -> Dict[str, Any]:
    """
    Add a new item to a wishlist

    Args:
        wishlist_id: The ID of the wishlist to add the item to
        url: The URL of the product
        title: Optional title (will be auto-detected if use_url_metadata=True)
        description: Optional description
        price: Optional price
        quantity: Quantity desired (default: 1)
        use_url_metadata: Whether to automatically fetch metadata from URL (default: True)
    """
    if not wishlist_id:
        raise ValueError("Wishlist ID is required")
    if not url:
        raise ValueError("URL is required")
    if quantity < 1:
        raise ValueError("Quantity must be >= 1")

    auth = await get_authenticated_service()
    result = await auth.create_wish(
        wishlist_id=wishlist_id,
        url=url,
        title=title,
        description=description,
        price=price,
        quantity=quantity,
        use_url_metadata=use_url_metadata,
    )

    # Handle the GraphQL response structure
    if (
        result.get("data")
        and result["data"].get("wish")
        and result["data"]["wish"].get("create")
    ):
        wish_data = result["data"]["wish"]["create"]
        return {
            "success": True,
            "message": "Wishlist item added successfully",
            "item": {
                "id": wish_data.get("id"),
                "title": wish_data.get("title"),
                "description": wish_data.get("description"),
                "url": wish_data.get("url"),
                "price": wish_data.get("price"),
                "currency": wish_data.get("currency"),
                "quantity": wish_data.get("quantity"),
                "image_url": wish_data.get("imageUrl"),
            },
        }
    else:
        return {
            "success": False,
            "message": "Failed to add wishlist item",
            "raw_response": result,
        }


@mcp.tool()
async def get_wishlist_details(wishlist_id: str) -> Dict[str, Any]:
    """
    Get details of a specific wishlist

    Args:
        wishlist_id: The ID of the wishlist
    """
    if not wishlist_id:
        raise ValueError("Wishlist ID is required")

    auth = await get_authenticated_service()
    wishlist_data = await auth.get_wishlist_page(wishlist_id)

    # Handle the GraphQL response structure
    if wishlist_data.get("data") and wishlist_data["data"].get("wishlist"):
        wishlist = wishlist_data["data"]["wishlist"]
        return {
            "id": wishlist.get("id"),
            "title": wishlist.get("title"),
            "description": wishlist.get("description"),
            "created_at": wishlist.get("createdAt"),
            "updated_at": wishlist.get("updatedAt"),
            "total_wishes": wishlist.get("totalWishes", 0),
            "slug": wishlist.get("slug"),
            "visibility": wishlist.get("visibility"),
            "owner": wishlist.get("user", {}),
        }
    else:
        raise ValueError(f"Wishlist {wishlist_id} not found")


@mcp.tool()
async def get_product_metadata(url: str, country_code: str = "DK") -> Dict[str, Any]:
    """
    Get product metadata from URL

    Args:
        url: Product URL to fetch metadata for
        country_code: Country code (default: "DK")
    """
    if not url:
        raise ValueError("URL is required")

    auth = await get_authenticated_service()
    result = await auth.get_product_by_url(url, country_code)

    # Extract and return the product data
    if (
        result.get("data")
        and result["data"].get("products")
        and result["data"]["products"].get("getByUrlV2")
    ):
        product = result["data"]["products"]["getByUrlV2"]
        return {
            "success": True,
            "product": {
                "title": product.get("title"),
                "description": product.get("description"),
                "price": product.get("price"),
                "currency": product.get("currency"),
                "image_url": product.get("imageUrl"),
                "brand": product.get("brand"),
                "availability": product.get("availability"),
                "url": product.get("url"),
            },
        }
    else:
        return {
            "success": False,
            "message": "No product metadata found for this URL",
        }


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
