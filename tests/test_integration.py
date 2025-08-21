#!/usr/bin/env python3
"""
Integration tests for the complete authentication and API flow
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.auth_service import AuthenticationService


class TestIntegration:
    """Integration tests for the complete flow"""

    def setup_method(self):
        """Set up test fixtures"""
        self.username = "test@example.com"
        self.password = "testpassword"

    @patch("src.browser_automation.async_playwright")
    @patch("src.auth_service.cache_service")
    async def test_complete_authentication_flow(
        self, mock_cache_service, mock_playwright
    ):
        """Test complete authentication flow from start to finish"""
        # Arrange
        mock_cache_service.get_user_profile = AsyncMock(return_value=None)
        mock_cache_service.set_user_profile = AsyncMock()

        # Set up mock playwright objects
        mock_playwright_instance = AsyncMock()
        mock_playwright.return_value.start = AsyncMock(
            return_value=mock_playwright_instance
        )

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # Mock successful login flow (no login required)
        mock_page.query_selector.return_value = None  # No login button found

        # Mock GraphQL response
        mock_page.evaluate.return_value = {
            "status": 200,
            "data": {"me": {"id": "123", "firstName": "Test", "lastName": "User"}},
            "headers": {},
            "usedAuthToken": True,
        }

        # Act
        async with AuthenticationService(self.username, self.password) as auth_service:
            profile = await auth_service.get_me()

        # Assert
        assert profile["me"]["id"] == "123"
        assert profile["me"]["firstName"] == "Test"

        # Verify browser setup was called
        mock_playwright_instance.chromium.launch.assert_called_once()
        mock_browser.new_context.assert_called_once()

        # Verify authentication flow
        assert mock_page.goto.call_count >= 2  # At least login and profile pages

        # Verify GraphQL request was made
        mock_page.evaluate.assert_called()

        # Verify caching was attempted
        mock_cache_service.set_user_profile.assert_called_once()

    @patch("src.browser_automation.async_playwright")
    @patch("src.auth_service.cache_service")
    async def test_complete_wishlist_flow(self, mock_cache_service, mock_playwright):
        """Test complete wishlist fetching flow"""
        # Arrange
        mock_cache_service.get_wishlists = AsyncMock(return_value=None)
        mock_cache_service.set_wishlists = AsyncMock()

        # Set up mock browser
        await self._setup_mock_browser(mock_playwright)

        # Mock GraphQL response for wishlists
        mock_wishlists_response = {
            "status": 200,
            "data": {
                "wishlists": {
                    "data": [
                        {"id": "wishlist1", "title": "My Wishlist"},
                        {"id": "wishlist2", "title": "Another Wishlist"},
                    ],
                    "totalCount": 2,
                }
            },
            "headers": {},
            "usedAuthToken": True,
        }

        # Act
        service = AuthenticationService(self.username, self.password)
        await service.authenticate()

        # Mock the GraphQL response for this specific call
        service.graphql_client.execute_query = AsyncMock(
            return_value=mock_wishlists_response["data"]
        )

        wishlists = await service.get_wishlists_paginated(limit=10, cursor=0)

        # Assert
        assert len(wishlists["wishlists"]["data"]) == 2
        assert wishlists["wishlists"]["data"][0]["title"] == "My Wishlist"

        # Verify caching was attempted
        mock_cache_service.set_wishlists.assert_called_once()

    @patch("src.browser_automation.async_playwright")
    @patch("src.auth_service.cache_service")
    async def test_create_wish_integration(self, mock_cache_service, mock_playwright):
        """Test complete wish creation flow with metadata fetching"""
        # Arrange
        await self._setup_mock_browser(mock_playwright)

        # Setup cache mock for invalidation
        mock_cache_service.invalidate_wishlist_cache = AsyncMock()

        wishlist_id = "wishlist123"
        product_url = "https://example.com/product"

        # Mock product metadata response
        mock_product_response = {
            "data": {
                "products": {
                    "getByUrlV2": {
                        "id": "prod123",
                        "title": "Amazing Product",
                        "description": "Great description",
                        "price": 199.99,
                        "currency": "DKK",
                        "imageUrls": ["https://example.com/image.jpg"],
                    }
                }
            }
        }

        # Mock wish creation response
        mock_create_response = {
            "data": {
                "wish": {
                    "create": {
                        "id": "wish123",
                        "title": "Amazing Product",
                        "price": 199.99,
                    }
                }
            }
        }

        # Act
        service = AuthenticationService(self.username, self.password)
        await service.authenticate()

        # Mock the GraphQL responses
        service.graphql_client.execute_query = AsyncMock()
        service.graphql_client.execute_query.side_effect = [
            mock_product_response["data"],  # First call for product metadata
            mock_create_response["data"],  # Second call for wish creation
        ]

        result = await service.create_wish(
            wishlist_id, product_url, use_url_metadata=True
        )

        # Assert
        assert result["wish"]["create"]["id"] == "wish123"
        assert result["wish"]["create"]["title"] == "Amazing Product"

        # Verify both GraphQL calls were made
        assert service.graphql_client.execute_query.call_count == 2

        # Verify cache invalidation was called
        mock_cache_service.invalidate_wishlist_cache.assert_called_once_with(
            wishlist_id
        )

    @patch("src.browser_automation.async_playwright")
    async def test_authentication_retry_on_expiry(self, mock_playwright):
        """Test authentication retry when session expires during API call"""
        # Arrange
        await self._setup_mock_browser(mock_playwright)

        service = AuthenticationService(self.username, self.password)
        await service.authenticate()

        # Mock GraphQL client to fail first, succeed second
        mock_graphql_client = AsyncMock()
        mock_graphql_client.execute_query.side_effect = [
            Exception("Authentication expired"),
            {"data": {"me": {"id": "123"}}},
        ]
        service.graphql_client = mock_graphql_client

        # Mock browser manager perform_login
        service.browser_manager._perform_login = AsyncMock()

        # Act
        result = await service._graphql_request("query { me { id } }")

        # Assert
        assert result == {"data": {"me": {"id": "123"}}}

        # Verify retry logic was triggered
        assert mock_graphql_client.execute_query.call_count == 2
        service.browser_manager._perform_login.assert_called_once()

    @patch("src.browser_automation.async_playwright")
    async def test_browser_cleanup_on_failure(self, mock_playwright):
        """Test browser cleanup is called when authentication fails"""
        # Arrange
        mock_playwright_instance = AsyncMock()
        mock_playwright.return_value.start.return_value = mock_playwright_instance

        mock_browser = AsyncMock()
        mock_context = AsyncMock()

        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.side_effect = Exception("Page creation failed")

        # Act & Assert
        service = AuthenticationService(self.username, self.password)

        with pytest.raises(Exception) as exc_info:
            await service.authenticate()

        assert "Authentication failed" in str(exc_info.value)

        # Verify cleanup was attempted
        # (cleanup should be called even if it fails)

    async def test_context_manager_cleanup(self):
        """Test context manager properly cleans up resources"""
        # Arrange
        service = AuthenticationService(self.username, self.password)
        service.authenticate = AsyncMock()
        service._cleanup = AsyncMock()

        # Act
        async with service as auth_service:
            assert auth_service == service
            service.authenticate.assert_called_once()

        # Assert
        service._cleanup.assert_called_once()

    @patch("src.browser_automation.async_playwright")
    async def test_multiple_api_calls_same_session(self, mock_playwright):
        """Test multiple API calls using the same authenticated session"""
        # Arrange
        await self._setup_mock_browser(mock_playwright)

        service = AuthenticationService(self.username, self.password)
        await service.authenticate()

        # Mock different GraphQL responses
        responses = [
            {"data": {"me": {"id": "123"}}},
            {"data": {"wishlists": {"data": []}}},
            {"data": {"wishlist": {"id": "wishlist123"}}},
        ]

        service.graphql_client.execute_query = AsyncMock()
        service.graphql_client.execute_query.side_effect = responses

        # Act
        profile_result = await service._graphql_request("query { me { id } }")
        wishlists_result = await service._graphql_request(
            "query { wishlists { data } }"
        )
        wishlist_result = await service._graphql_request(
            'query { wishlist(id: "123") { id } }'
        )

        # Assert
        assert profile_result == responses[0]
        assert wishlists_result == responses[1]
        assert wishlist_result == responses[2]

        # Verify all requests used the same client
        assert service.graphql_client.execute_query.call_count == 3

    async def _setup_mock_browser(self, mock_playwright):
        """Helper to set up mock browser for integration tests"""
        mock_playwright_instance = AsyncMock()
        mock_playwright.return_value.start = AsyncMock(
            return_value=mock_playwright_instance
        )

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # Mock successful page navigation and login detection
        mock_page.query_selector.return_value = None  # No login required

        return mock_playwright_instance
