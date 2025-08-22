#!/usr/bin/env python3
"""
Authentication service for Onskeskyen/GoWish API
Uses Playwright to maintain authenticated browser session for API requests
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from loguru import logger

from .browser_automation import BrowserManager
from .cache_service import cache_service
from .graphql_client import GraphQLClient
from .graphql_queries import (
    CREATE_WISH_MUTATION,
    GET_PRODUCT_BY_URL_QUERY,
    GET_USER_PROFILE_QUERY,
    GET_WISHLIST_PAGE_QUERY,
    GET_WISHLIST_WISHES_QUERY,
    GET_WISHLISTS_PAGINATED_QUERY,
)


class AuthenticationService:
    """
    Service that handles authentication with Onskeskyen using Playwright
    Maintains authenticated browser context for direct API requests
    """

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.authenticated_at: Optional[datetime] = None
        self.user_id: Optional[str] = None
        self.browser_manager = BrowserManager(username, password)
        self.graphql_client: Optional[GraphQLClient] = None

    async def authenticate(self) -> None:
        """Perform browser-based authentication and keep browser context active"""
        try:
            await self.browser_manager.setup_browser()
            await self.browser_manager.authenticate()

            # Setup GraphQL client with authenticated page
            if not self.browser_manager.page:
                raise Exception("Browser not setup - call setup_browser() first")
            self.graphql_client = GraphQLClient(self.browser_manager.page)
            self.authenticated_at = datetime.now()

        except Exception as e:
            await self._cleanup()
            raise Exception(f"Authentication failed: {e}") from e

    async def _graphql_request(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated GraphQL request using GraphQL client"""
        if not self.graphql_client:
            raise Exception(
                "GraphQL client not available - authentication may have failed"
            )

        try:
            return await self.graphql_client.execute_query(query, variables)
        except Exception as e:
            if "Authentication expired" in str(e):
                logger.warning("Authentication expired. Attempting re-authentication.")
                await self.browser_manager._perform_login()
                # Retry the request after re-authentication
                return await self.graphql_client.execute_query(query, variables)
            raise

    async def _cleanup(self) -> None:
        """Clean up browser resources"""
        if self.browser_manager:
            await self.browser_manager.cleanup()

    def is_authenticated(self) -> bool:
        """Check if the service is currently authenticated"""
        if not self.authenticated_at or not self.browser_manager.page:
            return False

        # Consider session expired after 8 hours
        expiry_time = self.authenticated_at + timedelta(hours=8)
        return datetime.now() < expiry_time

    async def refresh_authentication(self) -> None:
        """Refresh authentication if needed"""
        if not self.is_authenticated():
            await self._cleanup()
            await self.authenticate()

    # API method wrappers

    async def get_me(self) -> Dict[str, Any]:
        """Get current user profile with caching"""
        await self.refresh_authentication()

        # Try cache first (use username as user identifier)
        cached_profile = await cache_service.get_user_profile(self.username)
        if cached_profile:
            return cached_profile

        # Fetch from API using Playwright
        profile_data = await self._graphql_request(GET_USER_PROFILE_QUERY)

        logger.info(f"GraphQL response: {profile_data}")

        # Check for authentication errors
        if profile_data.get("errors"):
            error_message = profile_data["errors"][0].get("message", "Unknown error")
            if "authenticated" in error_message.lower():
                # Return empty profile data which will be handled by the model
                logger.error(f"Authentication error: {error_message}")
                return {"me": {}}

        # Extract and store user ID for future cache keys
        if profile_data.get("data", {}).get("me", {}).get("id"):
            self.user_id = profile_data["data"]["me"]["id"]

        # Cache the result
        await cache_service.set_user_profile(self.username, profile_data)

        return profile_data

    async def get_wishlists_paginated(
        self, limit: int = 50, cursor: int = 0
    ) -> Dict[str, Any]:
        """Get user wishlists with pagination and caching"""
        await self.refresh_authentication()

        # Try cache first
        user_key = self.user_id or self.username
        cached_wishlists = await cache_service.get_wishlists(user_key, limit, cursor)
        if cached_wishlists:
            return cached_wishlists

        # Fetch from API using Playwright
        variables = {
            "input": {"cursor": cursor, "limit": limit},
            "kinds": ["My", "Shared"],
        }

        wishlists_data = await self._graphql_request(
            GET_WISHLISTS_PAGINATED_QUERY, variables
        )

        # Cache the result
        await cache_service.set_wishlists(user_key, limit, cursor, wishlists_data)

        return wishlists_data

    async def get_wishlist_page(self, wishlist_id: str) -> Dict[str, Any]:
        """Get wishlist details with caching"""
        await self.refresh_authentication()

        # Try cache first
        cached_details = await cache_service.get_wishlist_details(wishlist_id)
        if cached_details:
            return cached_details

        # Fetch from API using Playwright
        variables = {"id": wishlist_id}
        details_data = await self._graphql_request(GET_WISHLIST_PAGE_QUERY, variables)

        # Cache the result
        await cache_service.set_wishlist_details(wishlist_id, details_data)

        return details_data

    async def get_wishlist_wishes(
        self, wishlist_id: str, limit: int = 24, cursor: int = 0
    ) -> Dict[str, Any]:
        """Get wishlist items with caching"""
        await self.refresh_authentication()

        # Try cache first
        cached_items = await cache_service.get_wishlist_items(
            wishlist_id, limit, cursor
        )
        if cached_items:
            return cached_items

        # Fetch from API using Playwright
        variables = {
            "id": wishlist_id,
            "input": {"cursor": cursor, "limit": limit},
            "sort": {"field": "index", "direction": "ASC"},
            "filter": None,
            "isLongQuery": True,
        }

        items_data = await self._graphql_request(GET_WISHLIST_WISHES_QUERY, variables)

        # Cache the result
        await cache_service.set_wishlist_items(wishlist_id, limit, cursor, items_data)

        return items_data

    async def get_product_by_url(
        self, url: str, country_code: str = "DK"
    ) -> Dict[str, Any]:
        """Get product metadata from URL using productByUrlV2 query"""
        await self.refresh_authentication()

        variables = {"url": url, "countryCode": country_code}
        result = await self._graphql_request(GET_PRODUCT_BY_URL_QUERY, variables)

        logger.info(f"get_product_by_url GraphQL response: {result}")
        return result

    async def create_wish(
        self,
        wishlist_id: str,
        url: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[float] = None,
        quantity: int = 1,
        use_url_metadata: bool = True,
    ) -> Dict[str, Any]:
        """Create a new wish item, optionally fetching metadata from URL first"""
        await self.refresh_authentication()

        # Step 1: Fetch product metadata from URL if requested
        product_metadata = None
        if use_url_metadata:
            try:
                logger.info(f"Fetching product metadata for URL: {url}")
                product_data = await self.get_product_by_url(url)

                # Extract product info from GraphQL response
                if (
                    product_data.get("data")
                    and product_data["data"].get("products")
                    and product_data["data"]["products"].get("getByUrlV2")
                ):
                    product_metadata = product_data["data"]["products"]["getByUrlV2"]
                    logger.info(f"Retrieved product metadata: {product_metadata}")
                else:
                    logger.warning(f"No product metadata found for URL: {url}")
            except Exception as e:
                logger.warning(f"Failed to fetch product metadata for {url}: {e}")
                # Continue with manual data if URL lookup fails

        # Step 2: Build wish input with metadata priority
        wish_input = {"url": url, "quantity": quantity, "labels": []}

        # Use fetched metadata if available, otherwise fall back to provided values
        if product_metadata:
            if not title and product_metadata.get("title"):
                wish_input["title"] = product_metadata["title"]
            elif title:
                wish_input["title"] = title

            if not description and product_metadata.get("description"):
                wish_input["description"] = product_metadata["description"]
            elif description:
                wish_input["description"] = description

            if not price and product_metadata.get("price"):
                wish_input["price"] = float(product_metadata["price"])
            elif price:
                wish_input["price"] = price

            # Add currency from metadata
            if product_metadata.get("currency"):
                wish_input["currency"] = product_metadata["currency"]

            # Add photos from metadata
            if product_metadata.get("imageUrls"):
                wish_input["photos"] = product_metadata["imageUrls"]

            # Add productRef from metadata
            wish_input["productRef"] = {
                "id": product_metadata.get("id"),
                "countryCode": product_metadata.get("countryCode"),
                "domainName": product_metadata.get("domainName"),
                "originalUrl": product_metadata.get("originalUrl"),
                "uurl": product_metadata.get("uurl"),
            }
        else:
            # Use provided values if no metadata was fetched
            if title:
                wish_input["title"] = title
            if description:
                wish_input["description"] = description
            if price:
                wish_input["price"] = price

        # Create wish using Playwright
        variables = {
            "input": wish_input,
            "wishlist": wishlist_id,
            "metadata": {},
        }

        result = await self._graphql_request(CREATE_WISH_MUTATION, variables)

        # Debug logging to understand the response structure
        logger.info(f"create_wish GraphQL response: {result}")

        # Invalidate related cache entries since we added a new item
        await cache_service.invalidate_wishlist_cache(wishlist_id)

        return result

    async def __aenter__(self):
        """Async context manager entry"""
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup()
