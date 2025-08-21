#!/usr/bin/env python3
"""
Network monitoring script to capture API calls from onskeskyen.dk
Uses the login functionality from main.py to authenticate and monitor network traffic
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


class APICallCapture:
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
                    # Schedule body capture asynchronously
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

    def save_to_file(self, filename: str = "captured_api_calls.json") -> None:
        """Save captured API calls to file"""
        output_path = Path(filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.api_calls, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved {len(self.api_calls)} API calls to {output_path}")


async def perform_wishlist_operations(page):
    """Perform comprehensive wishlist operations to capture all API calls"""
    logger.info("🎯 Starting comprehensive wishlist operations...")

    try:
        # 1. Add a new wish item and immediately delete it to capture both operations
        logger.info("\n1️⃣ Adding a new wish item and immediately deleting it...")
        await add_and_delete_wish_item(page)

    except Exception as e:
        logger.error(f"Error during wishlist operations: {e}")


async def add_and_delete_wish_item(page):
    """Add a new wish item and immediately delete it to capture both API calls"""
    try:
        # Wait a bit for the page to fully load (from main.py)
        await page.wait_for_timeout(2000)

        # Look for the new wish button (plus icon) - exact same logic as main.py
        new_wish_button_selector = 'div.NewWishCard__IconContainer-sc-78becbdd-2 img[src="/assets/plusGradient.svg"]'

        # Try to find the new wish button with wait_for_selector (like main.py)
        try:
            new_wish_button = await page.wait_for_selector(
                new_wish_button_selector, timeout=5000
            )
            if not new_wish_button:
                # Try alternative selector
                new_wish_button = await page.query_selector(
                    'img[alt="photo"][src="/assets/plusGradient.svg"]'
                )

            if new_wish_button:
                logger.info("  📤 Found 'New Wish' button")
            else:
                logger.error(
                    "  ❌ Could not find 'New Wish' button. Taking screenshot..."
                )
                await page.screenshot(path="debug_add_wish_screenshot.png")
                logger.info("  📸 Screenshot saved as debug_add_wish_screenshot.png")
                return
        except Exception as e:
            logger.error(f"  ❌ Error finding new wish button: {e}")
            await page.screenshot(path="debug_add_wish_screenshot.png")
            logger.info("  📸 Screenshot saved as debug_add_wish_screenshot.png")
            return

        # Test URL to add
        test_url = "https://www.lego.com/da-dk/product/speed-champions-mclaren-solus-gt-f1-lm-76918"
        logger.info(f"  📝 Adding test URL: {test_url}")

        # Click the new wish button to open popup (exact same as main.py)
        logger.info("  📤 Clicking 'New Wish' button...")
        await new_wish_button.click()
        await page.wait_for_timeout(1000)  # Wait for popup to appear

        # Fill URL in the popup input field (exact same as main.py)
        url_input_selector = 'input[data-cy="new-wish-input-automatic"][placeholder="Indsæt produktlink"]'
        url_input = await page.wait_for_selector(url_input_selector, timeout=5000)

        if url_input:
            logger.info("  📝 Filling URL in popup...")
            await url_input.fill(test_url)
            await page.wait_for_timeout(1000)

            # Check for "Spring over" (Skip) popup that sometimes appears (from main.py)
            try:
                skip_button = await page.query_selector(
                    'button:has-text("Spring over")'
                )
                if skip_button:
                    logger.info("  ⏭️ 'Spring over' popup detected, clicking skip...")
                    await skip_button.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass  # No skip popup, continue normally
        else:
            logger.error("  ❌ Could not find URL input in popup")
            return

        # Click submit button to add the wish (exact same as main.py)
        submit_button_selector = (
            'button[data-testid="new-wish-form-submit-btn"]:has-text("Tilføj ønske")'
        )
        submit_button = await page.query_selector(submit_button_selector)

        if not submit_button:
            # Try alternative selector
            submit_button = await page.query_selector(
                'button.GradientButton__CustomBtn-sc-b47f63b4-0:has-text("Tilføj ønske")'
            )

        if submit_button:
            logger.info("  ✅ Clicking 'Tilføj ønske' button...")
            await submit_button.click()
            await page.wait_for_timeout(
                3000
            )  # Wait for wish to be added (same as main.py)
            logger.success("  🎉 Wish added successfully!")

            # IMMEDIATELY try to delete the newly added item while it's still active
            logger.info("  🗑️ Immediately attempting to delete the newly added item...")
            await delete_newly_added_wish_item(page)

        else:
            logger.error("  ❌ Could not find submit button")
            # Try to close popup and continue (from main.py)
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)

    except Exception as e:
        logger.error(f"  ❌ Error in add_and_delete_wish_item: {e}")
        # Try to close any open popup (from main.py)
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)
        except Exception:
            pass


async def delete_newly_added_wish_item(page):
    """Delete the newly added wish item immediately while it's still the active/focused item"""
    try:
        # The newly added item should be visible and potentially highlighted/active
        # Look for the most recently added wish item (should be at index 0 or the first visible item)

        # Wait a moment for the page to update after adding
        await page.wait_for_timeout(1000)

        # Look for the newly added wish item - it might be highlighted or have a different state
        # Try to find the wish item that was just added
        new_wish_items = await page.query_selector_all('div[data-testid^="wish-card"]')

        if not new_wish_items:
            # Try alternative selectors for wish cards
            new_wish_items = await page.query_selector_all(
                '.WishCard, [class*="WishCard"], [class*="wish-card"]'
            )

        if new_wish_items and len(new_wish_items) > 0:
            logger.info(f"    🔍 Found {len(new_wish_items)} wish items after adding")

            # The newly added item should be the first one (index 0) in most cases
            newly_added_wish = new_wish_items[0]

            # Click on the newly added wish item to ensure it's selected/active
            logger.info("    📍 Clicking on the newly added wish item...")
            await newly_added_wish.click()
            await page.wait_for_timeout(1000)  # Wait for item to become active

            # Now immediately look for the "More button" while the item is active
            logger.info(
                "    📍 Step 1: Looking for 'More button menu icon' on active item..."
            )
            more_button = await page.query_selector(
                'img[alt="More button menu icon"][data-testid="moreButton"]'
            )

            if not more_button:
                # Try alternative selectors for more button
                more_button = await page.query_selector(
                    '[data-testid="moreButton"], img[src="/icons/dots.svg"]'
                )

            if more_button:
                logger.info("    🔘 Found 'More button', clicking...")
                await more_button.click()
                await page.wait_for_timeout(
                    500
                )  # Shorter wait to catch the menu quickly

                # Step 2: IMMEDIATELY look for "Slet ønske" in the dropdown menu
                logger.info("    📍 Step 2: Looking for 'Slet ønske' option...")
                delete_menu_item = await page.query_selector(
                    'span.CustomMenuItem__Text-sc-44786f2b-1:has-text("Slet ønske")'
                )

                if not delete_menu_item:
                    # Try alternative selectors with shorter timeout
                    delete_menu_item = await page.query_selector(
                        'span:has-text("Slet ønske"), [class*="MenuItem"]:has-text("Slet ønske")'
                    )

                if delete_menu_item:
                    logger.info("    🗑️ Found 'Slet ønske' menu item, clicking...")
                    await delete_menu_item.click()
                    await page.wait_for_timeout(500)

                    # Step 3: Click the delete option with trash icon in modal
                    logger.info("    📍 Step 3: Looking for delete option in modal...")
                    delete_option = await page.query_selector(
                        'div[data-testid="delete-wish-option-delete"]'
                    )

                    if not delete_option:
                        # Try alternative selectors for delete option
                        delete_option = await page.query_selector(
                            '[data-testid*="delete"], .DeleteWishModalContent__OptionElement-sc-950b2145-0'
                        )

                    if delete_option:
                        logger.info("    🗑️ Found delete option in modal, clicking...")
                        await delete_option.click()
                        await page.wait_for_timeout(500)

                        # Step 4: Click final "Slet" button to confirm deletion
                        logger.info(
                            "    📍 Step 4: Looking for final 'Slet' confirmation button..."
                        )
                        final_delete_button = await page.query_selector(
                            'button#button-modal-submit:has-text("Slet")'
                        )

                        if not final_delete_button:
                            # Try alternative selectors for final delete button
                            final_delete_button = await page.query_selector(
                                'button:has-text("Slet"), .FilledButton__CustomBtn-sc-5fef4482-0:has-text("Slet")'
                            )

                        if final_delete_button:
                            logger.info(
                                "    ✅ Found final 'Slet' button, confirming deletion..."
                            )
                            await final_delete_button.click()
                            await page.wait_for_timeout(
                                2000
                            )  # Wait for deletion to complete
                            logger.success("    🎉 Wish item deleted successfully!")
                        else:
                            logger.error(
                                "    ❌ Could not find final 'Slet' confirmation button"
                            )
                    else:
                        logger.error("    ❌ Could not find delete option in modal")
                else:
                    logger.error("    ❌ Could not find 'Slet ønske' menu item")
                    # Take a screenshot to debug
                    await page.screenshot(path="debug_delete_menu.png")
                    logger.info("    📸 Screenshot saved as debug_delete_menu.png")
            else:
                logger.error("    ❌ Could not find 'More button' (dots icon)")
                # Take a screenshot to debug
                await page.screenshot(path="debug_more_button.png")
                logger.info("    📸 Screenshot saved as debug_more_button.png")
        else:
            logger.info("    ℹ️ No wish items found after adding")

    except Exception as e:
        logger.error(f"    ❌ Error deleting newly added wish item: {e}")
        # Try to close any open modals
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)
        except Exception:
            pass


async def add_wish_item(page):
    """Add a new wish item to capture add API calls - follows main.py logic exactly"""
    try:
        # Wait a bit for the page to fully load (from main.py)
        await page.wait_for_timeout(2000)

        # Look for the new wish button (plus icon) - exact same logic as main.py
        new_wish_button_selector = 'div.NewWishCard__IconContainer-sc-78becbdd-2 img[src="/assets/plusGradient.svg"]'

        # Try to find the new wish button with wait_for_selector (like main.py)
        try:
            new_wish_button = await page.wait_for_selector(
                new_wish_button_selector, timeout=5000
            )
            if not new_wish_button:
                # Try alternative selector
                new_wish_button = await page.query_selector(
                    'img[alt="photo"][src="/assets/plusGradient.svg"]'
                )

            if new_wish_button:
                logger.info("  📤 Found 'New Wish' button")
            else:
                logger.error(
                    "  ❌ Could not find 'New Wish' button. Taking screenshot..."
                )
                await page.screenshot(path="debug_add_wish_screenshot.png")
                logger.info("  📸 Screenshot saved as debug_add_wish_screenshot.png")
                return
        except Exception as e:
            logger.error(f"  ❌ Error finding new wish button: {e}")
            await page.screenshot(path="debug_add_wish_screenshot.png")
            logger.info("  📸 Screenshot saved as debug_add_wish_screenshot.png")
            return

        # Test URL to add
        test_url = "https://www.lego.com/da-dk/product/speed-champions-mclaren-solus-gt-f1-lm-76918"
        logger.info(f"  📝 Adding test URL: {test_url}")

        # Click the new wish button to open popup (exact same as main.py)
        logger.info("  📤 Clicking 'New Wish' button...")
        await new_wish_button.click()
        await page.wait_for_timeout(1000)  # Wait for popup to appear

        # Fill URL in the popup input field (exact same as main.py)
        url_input_selector = 'input[data-cy="new-wish-input-automatic"][placeholder="Indsæt produktlink"]'
        url_input = await page.wait_for_selector(url_input_selector, timeout=5000)

        if url_input:
            logger.info("  📝 Filling URL in popup...")
            await url_input.fill(test_url)
            await page.wait_for_timeout(1000)

            # Check for "Spring over" (Skip) popup that sometimes appears (from main.py)
            try:
                skip_button = await page.query_selector(
                    'button:has-text("Spring over")'
                )
                if skip_button:
                    logger.info("  ⏭️ 'Spring over' popup detected, clicking skip...")
                    await skip_button.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass  # No skip popup, continue normally
        else:
            logger.error("  ❌ Could not find URL input in popup")
            return

        # Click submit button to add the wish (exact same as main.py)
        submit_button_selector = (
            'button[data-testid="new-wish-form-submit-btn"]:has-text("Tilføj ønske")'
        )
        submit_button = await page.query_selector(submit_button_selector)

        if not submit_button:
            # Try alternative selector
            submit_button = await page.query_selector(
                'button.GradientButton__CustomBtn-sc-b47f63b4-0:has-text("Tilføj ønske")'
            )

        if submit_button:
            logger.info("  ✅ Clicking 'Tilføj ønske' button...")
            await submit_button.click()
            await page.wait_for_timeout(
                3000
            )  # Wait for wish to be added (same as main.py)
            logger.success("  🎉 Wish added successfully!")
        else:
            logger.error("  ❌ Could not find submit button")
            # Try to close popup and continue (from main.py)
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)

    except Exception as e:
        logger.error(f"  ❌ Error adding wish item: {e}")
        # Try to close any open popup (from main.py)
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)
        except Exception:
            pass


async def delete_wish_item(page):
    """Delete a wish item to capture delete API calls - using exact UI flow"""
    try:
        # Look for existing wish items to delete
        wish_items = await page.query_selector_all('div[data-testid^="wish-card"]')

        if not wish_items:
            # Try alternative selectors for wish cards
            wish_items = await page.query_selector_all(
                '.WishCard, [class*="WishCard"], [class*="wish-card"]'
            )

        if wish_items and len(wish_items) > 0:
            logger.info(f"  🔍 Found {len(wish_items)} wish items")

            # Click on the first wish item to open it
            first_wish = wish_items[0]
            await first_wish.click()
            await page.wait_for_timeout(2000)

            # Step 1: Click the "More button menu icon" (dots icon)
            logger.info("  📍 Step 1: Looking for 'More button menu icon'...")
            more_button = await page.query_selector(
                'img[alt="More button menu icon"][data-testid="moreButton"]'
            )

            if not more_button:
                # Try alternative selectors for more button
                more_button = await page.query_selector(
                    '[data-testid="moreButton"], img[src="/icons/dots.svg"]'
                )

            if more_button:
                logger.info("  🔘 Found 'More button', clicking...")
                await more_button.click()
                await page.wait_for_timeout(1000)

                # Step 2: Click "Slet ønske" in the dropdown menu
                logger.info("  📍 Step 2: Looking for 'Slet ønske' option...")
                delete_menu_item = await page.query_selector(
                    'span.CustomMenuItem__Text-sc-44786f2b-1:has-text("Slet ønske")'
                )

                if not delete_menu_item:
                    # Try alternative selectors
                    delete_menu_item = await page.query_selector(
                        'span:has-text("Slet ønske"), [class*="MenuItem"]:has-text("Slet ønske")'
                    )

                if delete_menu_item:
                    logger.info("  🗑️ Found 'Slet ønske' menu item, clicking...")
                    await delete_menu_item.click()
                    await page.wait_for_timeout(1000)

                    # Step 3: Click the delete option with trash icon in modal
                    logger.info("  📍 Step 3: Looking for delete option in modal...")
                    delete_option = await page.query_selector(
                        'div[data-testid="delete-wish-option-delete"]'
                    )

                    if not delete_option:
                        # Try alternative selectors for delete option
                        delete_option = await page.query_selector(
                            '[data-testid*="delete"], .DeleteWishModalContent__OptionElement-sc-950b2145-0'
                        )

                    if delete_option:
                        logger.info("  🗑️ Found delete option in modal, clicking...")
                        await delete_option.click()
                        await page.wait_for_timeout(1000)

                        # Step 4: Click final "Slet" button to confirm deletion
                        logger.info(
                            "  📍 Step 4: Looking for final 'Slet' confirmation button..."
                        )
                        final_delete_button = await page.query_selector(
                            'button#button-modal-submit:has-text("Slet")'
                        )

                        if not final_delete_button:
                            # Try alternative selectors for final delete button
                            final_delete_button = await page.query_selector(
                                'button:has-text("Slet"), .FilledButton__CustomBtn-sc-5fef4482-0:has-text("Slet")'
                            )

                        if final_delete_button:
                            logger.info(
                                "  ✅ Found final 'Slet' button, confirming deletion..."
                            )
                            await final_delete_button.click()
                            await page.wait_for_timeout(3000)
                            logger.success("  🎉 Wish item deleted successfully!")
                        else:
                            logger.error(
                                "  ❌ Could not find final 'Slet' confirmation button"
                            )
                    else:
                        logger.error("  ❌ Could not find delete option in modal")
                else:
                    logger.error("  ❌ Could not find 'Slet ønske' menu item")
            else:
                logger.error("  ❌ Could not find 'More button' (dots icon)")
                # Close any open modal
                await page.keyboard.press("Escape")
        else:
            logger.info("  ℹ️ No wish items found to delete")

    except Exception as e:
        logger.error(f"  ❌ Error deleting wish item: {e}")
        # Try to close any open modals
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)
        except Exception:
            pass


async def navigate_to_user_wishlists(page):
    """Navigate to user's wishlist overview to capture 'get all wishlists' API"""
    logger.info("\n3️⃣ Navigating to user wishlists overview...")

    try:
        # Try different approaches to get to the user's wishlists
        navigation_attempts = [
            # Method 1: Direct URL to profile/wishlists
            lambda: page.goto("https://onskeskyen.dk/da/profile/wishlists"),
            # Method 2: Navigate to main profile page
            lambda: page.goto("https://onskeskyen.dk/da/profile"),
            # Method 3: Look for user menu/profile link
            lambda: navigate_via_user_menu(page),
            # Method 4: Navigate to home and look for "Mine ønsker"
            lambda: navigate_via_home(page),
        ]

        for i, attempt in enumerate(navigation_attempts, 1):
            try:
                logger.info(f"  📍 Attempt {i}: Trying navigation method...")
                await attempt()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)

                # Check if we successfully reached a page with wishlists
                if "profile" in page.url or "wishlist" in page.url:
                    logger.success(f"  ✅ Successfully navigated to: {page.url}")
                    break

            except Exception as e:
                logger.warning(f"  ⚠️ Navigation attempt {i} failed: {e}")
                continue

        logger.info("  🏁 User wishlist navigation completed")

    except Exception as e:
        logger.error(f"  ❌ Error navigating to user wishlists: {e}")


async def navigate_via_user_menu(page):
    """Try to navigate via user menu"""
    # Look for user avatar or profile button
    user_menu_selectors = [
        'img[alt*="profile"]',
        'img[alt*="avatar"]',
        '[data-testid*="profile"]',
        '[data-testid*="user"]',
        ".profile-menu",
        ".user-menu",
    ]

    for selector in user_menu_selectors:
        menu_button = await page.query_selector(selector)
        if menu_button:
            await menu_button.click()
            await page.wait_for_timeout(1000)

            # Look for wishlist link in dropdown
            wishlist_link = await page.query_selector(
                'a:has-text("ønsker"), a:has-text("Wishlist"), a:has-text("Mine")'
            )
            if wishlist_link:
                await wishlist_link.click()
                return
            break


async def navigate_via_home(page):
    """Try to navigate via home page"""
    await page.goto("https://onskeskyen.dk/da")
    await page.wait_for_timeout(2000)

    # Look for "Mine ønsker" or similar links
    home_links = [
        'a:has-text("Mine ønsker")',
        'a:has-text("Mine wishlists")',
        'a:has-text("Profil")',
        'a[href*="profile"]',
        'a[href*="wishlist"]',
    ]

    for selector in home_links:
        link = await page.query_selector(selector)
        if link:
            await link.click()
            await page.wait_for_timeout(2000)
            break


async def monitor_network_traffic():
    """Monitor network traffic while performing login and wishlist operations"""
    # Load environment variables
    load_dotenv()
    username = os.getenv("ONSKESKYEN_USERNAME")
    password = os.getenv("ONSKESKYEN_PASSWORD")

    if not username or not password:
        logger.error(
            "Please set ONSKESKYEN_USERNAME and ONSKESKYEN_PASSWORD in .env file"
        )
        return

    # Initialize API call capture
    api_capture = APICallCapture()

    async with async_playwright() as p:
        # Launch browser in headful mode so we can observe
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Set up network monitoring
        page.on("request", api_capture.capture_request)
        page.on("response", api_capture.capture_response)

        logger.info("🔍 Starting network monitoring...")
        logger.info("🌐 Navigate to onskeskyen.dk and perform login...")

        # Navigate to wishlist (updated to new wishlist)
        wishlist_url = "https://onskeskyen.dk/da/wishlists/j2pNAwngVECaYrSd"
        await page.goto(wishlist_url)
        await page.wait_for_load_state("networkidle")

        # Handle cookie consent popup (same as main.py)
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

        # Perform login process (same as main.py)
        try:
            initial_login_button = await page.query_selector(
                'button.Button__Container-sc-74e86c1a-0:has-text("Log ind")'
            )
            if initial_login_button:
                logger.info("🔐 Login required. Starting login process...")
                logger.info("Step 1: Clicking initial 'Log ind' button...")
                await initial_login_button.click()
                await page.wait_for_timeout(1000)

                # Step 2: Click "Fortsæt med e-mail"
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

                    # Step 3: Fill in email
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

                    # Step 4: Fill in password
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

                    # Step 5: Submit login
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

        # Wait for additional network activity
        logger.info("\n🕒 Waiting for additional API calls...")
        await page.wait_for_timeout(5000)

        # Add a wish item first to set up for manual delete
        logger.info("\n🎯 Adding a wish item for manual delete testing...")
        await add_wish_item(page)

        logger.info(
            "\n⏸️ MANUAL DELETE TIME: Please manually delete the newly added item now."
        )
        logger.info("This will capture the delete API endpoints.")
        input("Press Enter after you have manually deleted the item...")

        # Navigate to user's wishlist overview to capture "get all wishlists" API
        await navigate_to_user_wishlists(page)

        logger.info(f"\n📊 Captured {len(api_capture.api_calls)} API calls")

        # Save captured data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captured_api_calls_{timestamp}.json"
        api_capture.save_to_file(filename)

        # Show summary of captured calls
        logger.info("\n📋 Summary of captured API endpoints:")
        unique_urls = set()
        for call in api_capture.api_calls:
            if call["type"] == "request":
                unique_urls.add(f"{call['method']} {call['url']}")

        for url in sorted(unique_urls):
            logger.info(f"  • {url}")

        # Keep browser open for manual inspection
        input("\nPress Enter to close browser and finish monitoring...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(monitor_network_traffic())
