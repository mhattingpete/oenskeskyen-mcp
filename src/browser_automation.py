#!/usr/bin/env python3
"""
Browser automation and login logic for Onskeskyen authentication
"""

from typing import Dict

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class BrowserManager:
    """Handles browser automation for Onskeskyen authentication"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.captured_headers: Dict[str, str] = {}

    async def setup_browser(self) -> None:
        """Launch browser and setup context with request interception"""
        playwright = await async_playwright().start()

        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9,da;q=0.8",
            },
        )

        # Set up request interception to capture GraphQL headers
        captured_headers = {}

        async def capture_graphql_headers(route):
            if "api.gowish.com/graphql" in route.request.url:
                captured_headers.update(route.request.headers)
                logger.info(f"Captured GraphQL headers: {route.request.headers}")
            await route.continue_()

        await self.context.route("**/*", capture_graphql_headers)
        self.page = await self.context.new_page()
        self.captured_headers = captured_headers

    async def authenticate(self) -> None:
        """Perform complete authentication flow"""
        if not self.page:
            raise Exception("Browser not setup - call setup_browser() first")

        # Navigate to login page
        await self.page.goto("https://onskeskyen.dk/da/login")
        await self.page.wait_for_load_state("networkidle")

        # Handle cookie consent if present
        await self._handle_cookie_consent()

        # Perform login
        await self._perform_login()

        # Navigate to profile to ensure we're authenticated
        await self.page.goto("https://onskeskyen.dk/da/profile")
        await self.page.wait_for_load_state("networkidle")

        # Wait for any background requests to capture headers
        await self.page.wait_for_timeout(3000)

        print("✅ Authentication successful - browser session ready")

    async def _handle_cookie_consent(self) -> None:
        """Handle cookie consent dialog if present"""
        try:
            decline_button = await self.page.query_selector(
                'button#declineButton, button:has-text("Afvis alle")'
            )
            if decline_button:
                await decline_button.click()
                await self.page.wait_for_timeout(1000)
        except Exception:
            pass

    async def _perform_login(self) -> None:
        """Perform the actual login process"""
        try:
            logger.info("Starting login process using proven working method...")

            # Navigate to the wishlist page to trigger login flow
            wishlist_url = "https://onskeskyen.dk/da/wishlists/ZhgfNVLL8ydtRJgc"
            await self.page.goto(wishlist_url)
            await self.page.wait_for_load_state("networkidle")

            # Check if we need to log in (look for login button)
            initial_login_button = await self.page.query_selector(
                'button.Button__Container-sc-74e86c1a-0:has-text("Log ind")'
            )

            if initial_login_button:
                logger.info("Login required. Starting login process...")
                await self._execute_login_steps()
            else:
                logger.info("No login required or already logged in")
                # Navigate to profile to establish authenticated session
                await self.page.goto("https://onskeskyen.dk/da/profile")
                await self.page.wait_for_load_state("networkidle")

        except Exception as e:
            logger.error(f"Login process failed: {e}")
            await self._take_error_screenshot()
            raise Exception(f"Login process failed: {e}") from e

    async def _execute_login_steps(self) -> None:
        """Execute the multi-step login process"""
        # Step 1: Click the initial "Log ind" button
        logger.info("Step 1: Clicking initial 'Log ind' button...")
        initial_login_button = await self.page.query_selector(
            'button.Button__Container-sc-74e86c1a-0:has-text("Log ind")'
        )
        if initial_login_button:
            await initial_login_button.click()
            await self.page.wait_for_timeout(1000)

        # Step 2: Click "Fortsæt med e-mail" option
        email_option = await self._find_email_option()
        if email_option:
            logger.info("Step 2: Clicking 'Fortsæt med e-mail'...")
            await email_option.click()
            await self.page.wait_for_timeout(1000)

            # Step 3: Fill in email
            await self._fill_email()

            # Step 4: Fill in password
            await self._fill_password()

            # Step 5: Click final submit button
            await self._submit_login()

            logger.info(
                "Login completed, waiting for authentication to be established..."
            )
            await self.page.wait_for_timeout(2000)
        else:
            logger.error("Could not find 'Fortsæt med e-mail' option")

    async def _find_email_option(self):
        """Find the email login option"""
        email_option = await self.page.query_selector(
            'div.LoginInitialView__LoginOptionText-sc-c5136ca1-2:has-text("Fortsæt med e-mail")'
        )
        if not email_option:
            email_option = await self.page.query_selector('text="Fortsæt med e-mail"')
        return email_option

    async def _fill_email(self) -> None:
        """Fill in email field"""
        email_input = await self.page.query_selector(
            'input[name="email"][data-cy="signupEmailInput"]'
        )
        if not email_input:
            email_input = await self.page.query_selector('input[placeholder*="E-mail"]')

        if email_input:
            logger.info("Step 3: Filling in email...")
            await email_input.fill(self.username)
            await self.page.wait_for_timeout(500)

    async def _fill_password(self) -> None:
        """Fill in password field"""
        password_input = await self.page.query_selector(
            'input[type="password"][name="password"]'
        )
        if not password_input:
            password_input = await self.page.query_selector(
                'input[data-testid="loginPasswordInput"]'
            )

        if password_input:
            logger.info("Step 4: Filling in password...")
            await password_input.fill(self.password)
            await self.page.wait_for_timeout(500)

    async def _submit_login(self) -> None:
        """Submit the login form"""
        submit_button = await self.page.query_selector(
            'button[data-cy="registerNameNextButton"]:has-text("Log ind")'
        )
        if not submit_button:
            submit_button = await self.page.query_selector(
                'button.GradientButton__CustomBtn-sc-b47f63b4-0:has-text("Log ind")'
            )

        if submit_button:
            logger.info("Step 5: Clicking final 'Log ind' button...")
            await submit_button.click()
            await self.page.wait_for_load_state("networkidle")
            logger.success("Login completed successfully")
        else:
            logger.error("Could not find final submit button")

    async def _take_error_screenshot(self) -> None:
        """Take screenshot on error for debugging"""
        try:
            await self.page.screenshot(path="login_error.png")
            logger.info("Screenshot saved as login_error.png")
        except Exception:
            pass

    async def cleanup(self) -> None:
        """Clean up browser resources"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
