#!/usr/bin/env python3
"""
Tests for main authentication service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.auth_service import AuthenticationService


class TestAuthenticationService:
    """Test the main authentication service"""

    def setup_method(self):
        """Set up test fixtures"""
        self.username = "test@example.com"
        self.password = "testpassword"
        self.service = AuthenticationService(self.username, self.password)

    def test_init(self):
        """Test AuthenticationService initialization"""
        assert self.service.username == self.username
        assert self.service.password == self.password
        assert self.service.authenticated_at is None
        assert self.service.user_id is None
        assert self.service.browser_manager is not None
        assert self.service.graphql_client is None

    async def test_authenticate_success(self):
        """Test successful authentication"""
        # Arrange
        mock_browser_manager = AsyncMock()
        mock_page = AsyncMock()
        mock_browser_manager.page = mock_page
        self.service.browser_manager = mock_browser_manager

        # Act
        await self.service.authenticate()

        # Assert
        mock_browser_manager.setup_browser.assert_called_once()
        mock_browser_manager.authenticate.assert_called_once()
        assert self.service.graphql_client is not None
        assert self.service.authenticated_at is not None
        assert isinstance(self.service.authenticated_at, datetime)

    async def test_authenticate_failure(self):
        """Test authentication failure"""
        # Arrange
        mock_browser_manager = AsyncMock()
        mock_browser_manager.setup_browser.side_effect = Exception("Setup failed")
        self.service.browser_manager = mock_browser_manager

        # Mock cleanup method
        self.service._cleanup = AsyncMock()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await self.service.authenticate()

        assert "Authentication failed: Setup failed" in str(exc_info.value)
        self.service._cleanup.assert_called_once()

    async def test_graphql_request_success(self):
        """Test successful GraphQL request"""
        # Arrange
        mock_graphql_client = AsyncMock()
        expected_result = {"data": {"me": {"id": "123"}}}
        mock_graphql_client.execute_query.return_value = expected_result
        self.service.graphql_client = mock_graphql_client

        query = "query { me { id } }"
        variables = {"limit": 10}

        # Act
        result = await self.service._graphql_request(query, variables)

        # Assert
        assert result == expected_result
        mock_graphql_client.execute_query.assert_called_once_with(query, variables)

    async def test_graphql_request_no_client(self):
        """Test GraphQL request when client is not available"""
        # Arrange
        self.service.graphql_client = None
        query = "query { me { id } }"

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await self.service._graphql_request(query)

        assert "GraphQL client not available" in str(exc_info.value)

    async def test_graphql_request_auth_expired_retry(self):
        """Test GraphQL request with authentication expiry and retry"""
        # Arrange
        mock_graphql_client = AsyncMock()
        mock_browser_manager = AsyncMock()

        # First call fails with auth error, second succeeds
        expected_result = {"data": {"me": {"id": "123"}}}
        mock_graphql_client.execute_query.side_effect = [
            Exception("Authentication expired"),
            expected_result,
        ]

        self.service.graphql_client = mock_graphql_client
        self.service.browser_manager = mock_browser_manager

        query = "query { me { id } }"

        # Act
        result = await self.service._graphql_request(query)

        # Assert
        assert result == expected_result
        assert mock_graphql_client.execute_query.call_count == 2
        mock_browser_manager._perform_login.assert_called_once()

    async def test_cleanup(self):
        """Test cleanup functionality"""
        # Arrange
        mock_browser_manager = AsyncMock()
        self.service.browser_manager = mock_browser_manager

        # Act
        await self.service._cleanup()

        # Assert
        mock_browser_manager.cleanup.assert_called_once()

    def test_is_authenticated_true(self):
        """Test is_authenticated returns True when authenticated recently"""
        # Arrange
        mock_page = AsyncMock()
        self.service.browser_manager.page = mock_page
        self.service.authenticated_at = datetime.now() - timedelta(
            hours=1
        )  # 1 hour ago

        # Act
        result = self.service.is_authenticated()

        # Assert
        assert result is True

    def test_is_authenticated_false_no_auth_time(self):
        """Test is_authenticated returns False when not authenticated"""
        # Arrange
        self.service.authenticated_at = None

        # Act
        result = self.service.is_authenticated()

        # Assert
        assert result is False

    def test_is_authenticated_false_no_page(self):
        """Test is_authenticated returns False when no page available"""
        # Arrange
        self.service.authenticated_at = datetime.now()
        self.service.browser_manager.page = None

        # Act
        result = self.service.is_authenticated()

        # Assert
        assert result is False

    def test_is_authenticated_false_expired(self):
        """Test is_authenticated returns False when session expired"""
        # Arrange
        mock_page = AsyncMock()
        self.service.browser_manager.page = mock_page
        self.service.authenticated_at = datetime.now() - timedelta(
            hours=9
        )  # 9 hours ago

        # Act
        result = self.service.is_authenticated()

        # Assert
        assert result is False

    async def test_refresh_authentication_needed(self):
        """Test refresh authentication when needed"""
        # Arrange
        self.service.is_authenticated = MagicMock(return_value=False)
        self.service._cleanup = AsyncMock()
        self.service.authenticate = AsyncMock()

        # Act
        await self.service.refresh_authentication()

        # Assert
        self.service._cleanup.assert_called_once()
        self.service.authenticate.assert_called_once()

    async def test_refresh_authentication_not_needed(self):
        """Test refresh authentication when not needed"""
        # Arrange
        self.service.is_authenticated = MagicMock(return_value=True)
        self.service._cleanup = AsyncMock()
        self.service.authenticate = AsyncMock()

        # Act
        await self.service.refresh_authentication()

        # Assert
        self.service._cleanup.assert_not_called()
        self.service.authenticate.assert_not_called()

    @patch("src.auth_service.cache_service")
    async def test_get_me_from_cache(self, mock_cache_service):
        """Test get_me returns cached profile"""
        # Arrange
        cached_profile = {"data": {"me": {"id": "123", "name": "Test User"}}}
        mock_cache_service.get_user_profile = AsyncMock(return_value=cached_profile)
        self.service.refresh_authentication = AsyncMock()

        # Act
        result = await self.service.get_me()

        # Assert
        assert result == cached_profile
        self.service.refresh_authentication.assert_called_once()
        mock_cache_service.get_user_profile.assert_called_once_with(self.username)

    @patch("src.auth_service.cache_service")
    async def test_get_me_from_api(self, mock_cache_service):
        """Test get_me fetches from API when not cached"""
        # Arrange
        mock_cache_service.get_user_profile = AsyncMock(return_value=None)
        mock_cache_service.set_user_profile = AsyncMock()
        api_response = {"data": {"me": {"id": "123", "name": "Test User"}}}

        self.service.refresh_authentication = AsyncMock()
        self.service._graphql_request = AsyncMock(return_value=api_response)

        # Act
        result = await self.service.get_me()

        # Assert
        assert result == api_response
        mock_cache_service.set_user_profile.assert_called_once_with(
            self.username, api_response
        )
        assert self.service.user_id == "123"

    @patch("src.auth_service.cache_service")
    async def test_get_wishlists_paginated_from_cache(self, mock_cache_service):
        """Test get_wishlists_paginated returns cached data"""
        # Arrange
        cached_wishlists = {"data": {"wishlists": []}}
        mock_cache_service.get_wishlists = AsyncMock(return_value=cached_wishlists)
        self.service.refresh_authentication = AsyncMock()

        # Act
        result = await self.service.get_wishlists_paginated(limit=10, cursor=0)

        # Assert
        assert result == cached_wishlists
        self.service.refresh_authentication.assert_called_once()

    @patch("src.auth_service.cache_service")
    async def test_get_product_by_url(self, mock_cache_service):
        """Test get_product_by_url functionality"""
        # Arrange
        url = "https://example.com/product"
        country_code = "DK"
        api_response = {"data": {"products": {"getByUrlV2": {"id": "123"}}}}

        self.service.refresh_authentication = AsyncMock()
        self.service._graphql_request = AsyncMock(return_value=api_response)

        # Act
        result = await self.service.get_product_by_url(url, country_code)

        # Assert
        assert result == api_response
        self.service._graphql_request.assert_called_once()

        # Check the variables passed to GraphQL request
        call_args = self.service._graphql_request.call_args
        variables = call_args[0][1]
        assert variables["url"] == url
        assert variables["countryCode"] == country_code

    @patch("src.auth_service.cache_service")
    async def test_create_wish_with_metadata(self, mock_cache_service):
        """Test create_wish with URL metadata fetching"""
        # Arrange
        wishlist_id = "wishlist123"
        url = "https://example.com/product"
        title = "Test Product"

        # Mock product metadata response
        product_metadata = {
            "id": "prod123",
            "title": "Fetched Title",
            "description": "Fetched Description",
            "price": 99.99,
            "currency": "DKK",
            "imageUrls": ["https://example.com/image.jpg"],
        }

        product_response = {"data": {"products": {"getByUrlV2": product_metadata}}}

        create_response = {"data": {"wish": {"create": {"id": "wish123"}}}}

        self.service.refresh_authentication = AsyncMock()
        self.service.get_product_by_url = AsyncMock(return_value=product_response)
        self.service._graphql_request = AsyncMock(return_value=create_response)
        mock_cache_service.invalidate_wishlist_cache = AsyncMock()

        # Act
        result = await self.service.create_wish(
            wishlist_id, url, title=title, use_url_metadata=True
        )

        # Assert
        assert result == create_response
        self.service.get_product_by_url.assert_called_once_with(url)

        # Verify the wish input was built correctly
        call_args = self.service._graphql_request.call_args
        variables = call_args[0][1]
        wish_input = variables["input"]

        # Should use provided title over fetched title
        assert wish_input["title"] == title
        assert wish_input["description"] == "Fetched Description"
        assert wish_input["price"] == 99.99
        assert wish_input["currency"] == "DKK"
        assert wish_input["photos"] == ["https://example.com/image.jpg"]

        mock_cache_service.invalidate_wishlist_cache.assert_called_once_with(
            wishlist_id
        )

    async def test_context_manager_enter(self):
        """Test async context manager entry"""
        # Arrange
        self.service.authenticate = AsyncMock()

        # Act
        result = await self.service.__aenter__()

        # Assert
        assert result == self.service
        self.service.authenticate.assert_called_once()

    async def test_context_manager_exit(self):
        """Test async context manager exit"""
        # Arrange
        self.service._cleanup = AsyncMock()

        # Act
        await self.service.__aexit__(None, None, None)

        # Assert
        self.service._cleanup.assert_called_once()
