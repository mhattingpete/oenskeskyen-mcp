#!/usr/bin/env python3
"""
Simple manual delete monitor - opens browser for you to manually delete an item
while capturing the delete API calls
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from loguru import logger
from playwright.async_api import Request, Response, async_playwright


class DeleteAPICapture:
    def __init__(self):
        self.api_calls: List[Dict[str, Any]] = []

    def capture_request(self, request: Request) -> None:
        """Capture outgoing requests"""
        if self.is_api_request(request.url):
            call_data = {
                "timestamp": datetime.now().isoformat(),
                "type": "request",
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "post_data": request.post_data if request.post_data else None,
            }
            self.api_calls.append(call_data)
            logger.info(f"📤 Request: {request.method} {request.url}")

    def capture_response(self, response: Response) -> None:
        """Capture incoming responses"""
        if self.is_api_request(response.url):
            call_data = {
                "timestamp": datetime.now().isoformat(),
                "type": "response",
                "status": response.status,
                "url": response.url,
                "headers": dict(response.headers),
            }

            # Try to capture response body for API calls
            if response.status == 200:
                try:
                    asyncio.create_task(
                        self._capture_response_body(response, call_data)
                    )
                except Exception as e:
                    logger.error(f"Error capturing response body: {e}")

            self.api_calls.append(call_data)
            logger.info(f"📥 Response: {response.status} {response.url}")

    async def _capture_response_body(
        self, response: Response, call_data: Dict[str, Any]
    ) -> None:
        """Capture response body asynchronously"""
        try:
            body = await response.body()
            content_type = response.headers.get("content-type", "")

            if "application/json" in content_type:
                try:
                    call_data["body"] = json.loads(body.decode("utf-8"))
                except json.JSONDecodeError:
                    call_data["body"] = body.decode("utf-8")
            else:
                call_data["body"] = (
                    body.decode("utf-8")
                    if len(body) < 10000
                    else f"<large response: {len(body)} bytes>"
                )
        except Exception as e:
            call_data["body_error"] = str(e)

    @staticmethod
    def is_api_request(url: str) -> bool:
        """Check if URL is an API request we want to monitor"""
        api_patterns = [
            "api.gowish.com",
            "auth.gowish.com",
            "onskeskyen.dk/api",
            "graphql",
            "/api/",
            "gowish",
        ]
        return any(pattern in url.lower() for pattern in api_patterns)

    def save_to_file(self, filename: str = "delete_api_calls.json") -> None:
        """Save captured API calls to file"""
        output_path = Path(filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.api_calls, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved {len(self.api_calls)} API calls to {output_path}")


async def manual_delete_monitor():
    """Monitor for manual delete operations"""
    load_dotenv()
    username = os.getenv("ONSKESKYEN_USERNAME")
    password = os.getenv("ONSKESKYEN_PASSWORD")

    if not username or not password:
        logger.error(
            "Please set ONSKESKYEN_USERNAME and ONSKESKYEN_PASSWORD in .env file"
        )
        return

    # Initialize API call capture
    api_capture = DeleteAPICapture()

    async with async_playwright() as p:
        # Launch browser in headful mode
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Set up network monitoring
        page.on("request", api_capture.capture_request)
        page.on("response", api_capture.capture_response)

        logger.info("🔍 Starting manual delete monitoring...")
        logger.info("🌐 Opening browser with wishlist...")

        # Navigate to wishlist
        wishlist_url = "https://onskeskyen.dk/da/wishlists/j2pNAwngVECaYrSd"
        await page.goto(wishlist_url)
        await page.wait_for_load_state("networkidle")

        # Handle cookie consent popup
        try:
            decline_button = await page.query_selector(
                'button#declineButton, button:has-text("Afvis alle")'
            )
            if decline_button:
                logger.info("Cookie consent popup detected, declining cookies...")
                await decline_button.click()
                await page.wait_for_timeout(1000)
        except Exception as e:
            logger.debug(f"No cookie popup or already handled: {e}")

        # Perform login if needed
        try:
            initial_login_button = await page.query_selector(
                'button.Button__Container-sc-74e86c1a-0:has-text("Log ind")'
            )
            if initial_login_button:
                logger.info("🔐 Login required. Starting login process...")
                logger.info("Step 1: Clicking initial 'Log ind' button...")
                await initial_login_button.click()
                await page.wait_for_timeout(1000)

                # Continue with email login
                email_option = await page.query_selector(
                    'div.LoginInitialView__LoginOptionText-sc-c5136ca1-2:has-text("Fortsæt med e-mail")'
                )
                if not email_option:
                    email_option = await page.query_selector(
                        'text="Fortsæt med e-mail"'
                    )

                if email_option:
                    logger.info("Step 2: Clicking 'Fortsæt med e-mail'...")
                    await email_option.click()
                    await page.wait_for_timeout(1000)

                    # Fill email
                    email_input = await page.query_selector(
                        'input[name="email"][data-cy="signupEmailInput"]'
                    )
                    if not email_input:
                        email_input = await page.query_selector(
                            'input[placeholder*="E-mail"]'
                        )

                    if email_input:
                        logger.info("Step 3: Filling in email...")
                        await email_input.fill(username)
                        await page.wait_for_timeout(500)

                    # Fill password
                    password_input = await page.query_selector(
                        'input[type="password"][name="password"]'
                    )
                    if not password_input:
                        password_input = await page.query_selector(
                            'input[data-testid="loginPasswordInput"]'
                        )

                    if password_input:
                        logger.info("Step 4: Filling in password...")
                        await password_input.fill(password)
                        await page.wait_for_timeout(500)

                    # Submit login
                    submit_button = await page.query_selector(
                        'button[data-cy="registerNameNextButton"]:has-text("Log ind")'
                    )
                    if not submit_button:
                        submit_button = await page.query_selector(
                            'button.GradientButton__CustomBtn-sc-b47f63b4-0:has-text("Log ind")'
                        )

                    if submit_button:
                        logger.info("Step 5: Clicking final 'Log ind' button...")
                        await submit_button.click()
                        await page.wait_for_load_state("networkidle")
                        logger.success("✅ Login completed successfully")

                # Navigate back to wishlist if needed
                if wishlist_url not in page.url:
                    logger.info("Navigating back to wishlist...")
                    await page.goto(wishlist_url)
                    await page.wait_for_load_state("networkidle")
            else:
                logger.info("No login required or already logged in")
        except Exception as e:
            logger.debug(f"Login process completed with: {e}")

        logger.info("\n🎯 MANUAL DELETE INSTRUCTIONS:")
        logger.info("1. Find a wish item in the wishlist")
        logger.info("2. Click the 'More' button (three dots) on an item")
        logger.info("3. Click 'Slet ønske' in the dropdown")
        logger.info("4. Follow the delete confirmation steps")
        logger.info("5. The delete API calls will be captured automatically")
        logger.info("\n⏸️ Browser will stay open until you close this script...")
        logger.info("Press Ctrl+C when you're done with manual testing")

        try:
            # Keep the browser open indefinitely for manual testing
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n🛑 Manual testing completed")

        # Save captured data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"manual_delete_calls_{timestamp}.json"
        api_capture.save_to_file(filename)

        # Show summary
        logger.info(f"\n📊 Captured {len(api_capture.api_calls)} API calls")
        unique_urls = set()
        for call in api_capture.api_calls:
            if call["type"] == "request":
                unique_urls.add(f"{call['method']} {call['url']}")

        if unique_urls:
            logger.info("\n📋 Summary of captured API endpoints:")
            for url in sorted(unique_urls):
                logger.info(f"  • {url}")
        else:
            logger.info("\n📋 No API calls captured during manual testing")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(manual_delete_monitor())
