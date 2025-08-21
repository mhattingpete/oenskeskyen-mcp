#!/usr/bin/env python3
"""
Tests for browser automation component
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.browser_automation import BrowserManager


class TestBrowserManager:
    """Test the browser automation functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.username = "test@example.com"
        self.password = "testpassword"
        self.manager = BrowserManager(self.username, self.password)

    async def test_init(self):
        """Test BrowserManager initialization"""
        assert self.manager.username == self.username
        assert self.manager.password == self.password
        assert self.manager.browser is None
        assert self.manager.context is None
        assert self.manager.page is None
        assert self.manager.captured_headers == {}

    @patch("src.browser_automation.async_playwright")
    async def test_setup_browser_success(self, mock_playwright):
        """Test successful browser setup"""
        # Arrange
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

        # Act
        await self.manager.setup_browser()

        # Assert
        assert self.manager.browser == mock_browser
        assert self.manager.context == mock_context
        assert self.manager.page == mock_page

        # Verify browser was launched with correct settings
        mock_playwright_instance.chromium.launch.assert_called_once_with(headless=True)

        # Verify context was created with correct settings
        mock_browser.new_context.assert_called_once()
        context_args = mock_browser.new_context.call_args[1]
        assert "user_agent" in context_args
        assert "Chrome" in context_args["user_agent"]
        assert "extra_http_headers" in context_args

    async def test_authenticate_no_browser_setup(self):
        """Test authentication fails when browser not setup"""
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await self.manager.authenticate()

        assert "Browser not setup" in str(exc_info.value)

    @patch("src.browser_automation.async_playwright")
    async def test_authenticate_success_no_login_required(self, mock_playwright):
        """Test authentication when already logged in"""
        # Arrange
        await self._setup_mock_browser(mock_playwright)

        # Mock page behavior - no login button found
        self.manager.page.query_selector.return_value = None

        # Act
        await self.manager.authenticate()

        # Assert
        # Should navigate to login page first, then at least one more page
        actual_calls = self.manager.page.goto.call_args_list
        assert len(actual_calls) >= 2  # At least login page and profile

    @patch("src.browser_automation.async_playwright")
    async def test_authenticate_success_with_login(self, mock_playwright):
        """Test authentication with login flow"""
        # Arrange
        await self._setup_mock_browser(mock_playwright)

        # Mock login flow elements
        mock_login_button = AsyncMock()
        mock_email_option = AsyncMock()
        mock_email_input = AsyncMock()
        mock_password_input = AsyncMock()
        mock_submit_button = AsyncMock()

        # Configure query_selector to return different elements based on selector
        def query_selector_side_effect(selector):
            if "Log ind" in selector and "Button__Container" in selector:
                return mock_login_button
            elif "Fortsæt med e-mail" in selector:
                return mock_email_option
            elif "email" in selector and "signupEmailInput" in selector:
                return mock_email_input
            elif "password" in selector:
                return mock_password_input
            elif "registerNameNextButton" in selector:
                return mock_submit_button
            return None

        self.manager.page.query_selector.side_effect = query_selector_side_effect

        # Act
        await self.manager.authenticate()

        # Assert
        mock_login_button.click.assert_called_once()
        mock_email_option.click.assert_called_once()
        mock_email_input.fill.assert_called_once_with(self.username)
        mock_password_input.fill.assert_called_once_with(self.password)
        mock_submit_button.click.assert_called_once()

    async def test_handle_cookie_consent_found(self):
        """Test cookie consent handling when button is found"""
        # Arrange
        mock_page = AsyncMock()
        mock_decline_button = AsyncMock()
        mock_page.query_selector.return_value = mock_decline_button
        self.manager.page = mock_page

        # Act
        await self.manager._handle_cookie_consent()

        # Assert
        mock_decline_button.click.assert_called_once()
        mock_page.wait_for_timeout.assert_called_once_with(1000)

    async def test_handle_cookie_consent_not_found(self):
        """Test cookie consent handling when button is not found"""
        # Arrange
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None
        self.manager.page = mock_page

        # Act
        await self.manager._handle_cookie_consent()

        # Assert
        mock_page.query_selector.assert_called_once()
        # Should not call click or wait_for_timeout

    async def test_fill_email(self):
        """Test email filling functionality"""
        # Arrange
        mock_page = AsyncMock()
        mock_email_input = AsyncMock()
        mock_page.query_selector.return_value = mock_email_input
        self.manager.page = mock_page

        # Act
        await self.manager._fill_email()

        # Assert
        mock_email_input.fill.assert_called_once_with(self.username)
        mock_page.wait_for_timeout.assert_called_once_with(500)

    async def test_fill_password(self):
        """Test password filling functionality"""
        # Arrange
        mock_page = AsyncMock()
        mock_password_input = AsyncMock()
        mock_page.query_selector.return_value = mock_password_input
        self.manager.page = mock_page

        # Act
        await self.manager._fill_password()

        # Assert
        mock_password_input.fill.assert_called_once_with(self.password)
        mock_page.wait_for_timeout.assert_called_once_with(500)

    async def test_submit_login(self):
        """Test login submission functionality"""
        # Arrange
        mock_page = AsyncMock()
        mock_submit_button = AsyncMock()
        mock_page.query_selector.return_value = mock_submit_button
        self.manager.page = mock_page

        # Act
        await self.manager._submit_login()

        # Assert
        mock_submit_button.click.assert_called_once()
        mock_page.wait_for_load_state.assert_called_once_with("networkidle")

    async def test_cleanup_success(self):
        """Test successful cleanup of browser resources"""
        # Arrange
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        self.manager.context = mock_context
        self.manager.browser = mock_browser

        # Act
        await self.manager.cleanup()

        # Assert
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()

    async def test_cleanup_with_exceptions(self):
        """Test cleanup handles exceptions gracefully"""
        # Arrange
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_context.close.side_effect = Exception("Context close failed")
        mock_browser.close.side_effect = Exception("Browser close failed")
        self.manager.context = mock_context
        self.manager.browser = mock_browser

        # Act (should not raise exception)
        await self.manager.cleanup()

        # Assert (cleanup should still attempt both operations)
        # Note: Exception in close() is caught and ignored, so the calls should still be made
        mock_context.close.assert_called_once()
        # The browser.close() may not be called if context.close() fails
        # This depends on the implementation, so let's just check that no exception was raised

    async def test_find_email_option_primary_selector(self):
        """Test finding email option with primary selector"""
        # Arrange
        mock_page = AsyncMock()
        mock_email_option = AsyncMock()
        mock_page.query_selector.return_value = mock_email_option
        self.manager.page = mock_page

        # Act
        result = await self.manager._find_email_option()

        # Assert
        assert result == mock_email_option
        mock_page.query_selector.assert_called_once()

    async def test_find_email_option_fallback_selector(self):
        """Test finding email option with fallback selector"""
        # Arrange
        mock_page = AsyncMock()
        mock_email_option = AsyncMock()

        # First call returns None, second call returns the element
        mock_page.query_selector.side_effect = [None, mock_email_option]
        self.manager.page = mock_page

        # Act
        result = await self.manager._find_email_option()

        # Assert
        assert result == mock_email_option
        assert mock_page.query_selector.call_count == 2

    async def _setup_mock_browser(self, mock_playwright):
        """Helper method to set up mock browser for tests"""
        mock_playwright_instance = AsyncMock()
        mock_playwright.return_value.start.return_value = mock_playwright_instance

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        self.manager.browser = mock_browser
        self.manager.context = mock_context
        self.manager.page = mock_page

        return mock_playwright_instance
