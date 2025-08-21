#!/usr/bin/env python3
"""
FastAPI application for Onskeskyen/GoWish API integration
Provides REST endpoints that wrap the reconstructed GraphQL API client
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.auth_service import AuthenticationService
from src.cache_service import cache_service, start_cache_cleanup_task
from src.models import (
    AddWishlistItemRequest,
    AddWishlistItemResponse,
    UserProfile,
    Wishlist,
    WishlistItem,
)

# Load environment variables
load_dotenv()


# Global authentication service instance
auth_service_x: Optional[AuthenticationService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the authentication service on startup"""
    global auth_service_x

    username = os.getenv("ONSKESKYEN_USERNAME")
    password = os.getenv("ONSKESKYEN_PASSWORD")

    if not username or not password:
        raise RuntimeError(
            "Missing required environment variables: ONSKESKYEN_USERNAME and ONSKESKYEN_PASSWORD"
        )

    try:
        auth_service_x = AuthenticationService(username, password)
        await auth_service_x.authenticate()
        logger.success(f"✅ Authentication successful for user: {username}")

        # Start cache cleanup background task
        asyncio.create_task(start_cache_cleanup_task())
        logger.info("🧹 Cache cleanup task started")

    except Exception as e:
        raise RuntimeError(f"Failed to authenticate: {e}") from e
    yield


# Initialize FastAPI app
app = FastAPI(
    title="Onskeskyen API Gateway",
    description="REST API gateway for Onskeskyen/GoWish wishlist operations",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_auth_service() -> AuthenticationService:
    """Dependency to get the authenticated service"""
    if auth_service_x is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialized",
        )
    return auth_service_x


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "authenticated": auth_service_x is not None
        and auth_service_x.is_authenticated(),
        "cache_stats": cache_service.get_stats(),
    }


@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    return {
        "cache_stats": cache_service.get_stats(),
        "timestamp": datetime.now().isoformat(),
    }


@app.delete("/cache")
async def clear_cache():
    """Clear all cache entries"""
    await cache_service.clear()
    return {
        "message": "Cache cleared successfully",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/me", response_model=UserProfile)
async def get_me(
    auth: AuthenticationService = Depends(get_auth_service),
) -> UserProfile:
    """Get current user profile information"""
    try:
        user_data = await auth.get_me()
        return UserProfile.from_api_response(user_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}",
        ) from e


@app.get("/wishlists", response_model=List[Wishlist])
async def get_wishlists(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: int = Query(default=0, ge=0),
    auth: AuthenticationService = Depends(get_auth_service),
) -> List[Wishlist]:
    """Get all user wishlists with pagination"""
    try:
        wishlists_data = await auth.get_wishlists_paginated(limit=limit, cursor=cursor)
        logger.debug(f"Debug - wishlists_data structure: {wishlists_data}")

        # Handle the GraphQL response structure
        if wishlists_data.get("data") and wishlists_data["data"].get("wishlists"):
            wishlists = wishlists_data["data"]["wishlists"].get("data", [])
        else:
            wishlists = []

        return [Wishlist.from_api_response(wl) for wl in wishlists]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wishlists: {str(e)}",
        ) from e


@app.get("/wishlists/{wishlist_id}/items", response_model=List[WishlistItem])
async def get_wishlist_items(
    wishlist_id: str,
    limit: int = Query(default=24, ge=1, le=100),
    cursor: int = Query(default=0, ge=0),
    auth: AuthenticationService = Depends(get_auth_service),
) -> List[WishlistItem]:
    """Get items from a specific wishlist"""
    try:
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

        return [WishlistItem.from_api_response(item) for item in wishes]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wishlist items: {str(e)}",
        ) from e


@app.post("/wishlists/{wishlist_id}/items", response_model=AddWishlistItemResponse)
async def add_wishlist_item(
    wishlist_id: str,
    request: AddWishlistItemRequest,
    auth: AuthenticationService = Depends(get_auth_service),
) -> AddWishlistItemResponse:
    """Add a new item to a wishlist"""
    try:
        result = await auth.create_wish(
            wishlist_id=wishlist_id,
            url=str(request.url),
            title=request.title,
            description=request.description,
            price=float(request.price) if request.price else None,
            quantity=request.quantity,
            use_url_metadata=request.use_url_metadata,
        )

        # Handle the GraphQL response structure
        if (
            result.get("data")
            and result["data"].get("wish")
            and result["data"]["wish"].get("create")
        ):
            wish_data = result["data"]["wish"]["create"]
        else:
            # Fallback to empty wish data if structure is unexpected
            wish_data = {}

        return AddWishlistItemResponse(
            success=True,
            message="Wishlist item added successfully",
            item=WishlistItem.from_api_response(wish_data),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add wishlist item: {str(e)}",
        ) from e


@app.delete("/wishlists/{wishlist_id}/items/{item_id}")
async def delete_wishlist_item(
    wishlist_id: str,
    item_id: str,
    auth: AuthenticationService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """Delete an item from a wishlist"""
    # TODO: Implement when delete endpoint is captured
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete functionality not yet implemented - delete API endpoint not captured",
    )


@app.get("/wishlists/{wishlist_id}", response_model=Wishlist)
async def get_wishlist(
    wishlist_id: str, auth: AuthenticationService = Depends(get_auth_service)
) -> Wishlist:
    """Get details of a specific wishlist"""
    try:
        wishlist_data = await auth.get_wishlist_page(wishlist_id)

        # Handle the GraphQL response structure
        if wishlist_data.get("data") and wishlist_data["data"].get("wishlist"):
            wishlist = wishlist_data["data"]["wishlist"]
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wishlist {wishlist_id} not found",
            )

        return Wishlist.from_api_response(wishlist)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wishlist: {str(e)}",
        ) from e


@app.get("/products/metadata")
async def get_product_metadata(
    url: str = Query(..., description="Product URL to fetch metadata for"),
    country_code: str = Query(default="DK", description="Country code"),
    auth: AuthenticationService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """Get product metadata from URL using productByUrlV2 query"""
    try:
        result = await auth.get_product_by_url(url, country_code)

        # Extract and return the product data
        if (
            result.get("data")
            and result["data"].get("products")
            and result["data"]["products"].get("getByUrlV2")
        ):
            return {
                "success": True,
                "product": result["data"]["products"]["getByUrlV2"],
                "raw_response": result,
            }
        else:
            return {
                "success": False,
                "message": "No product metadata found for this URL",
                "raw_response": result,
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get product metadata: {str(e)}",
        ) from e


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info"),
    )
