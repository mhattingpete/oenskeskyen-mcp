#!/usr/bin/env python3
"""
Automate adding URLs to Ønskeskyen wishlist using Playwright
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from playwright.async_api import async_playwright


async def add_urls_to_wishlist():
    # Load environment variables
    load_dotenv()
    username = os.getenv("ONSKESKYEN_USERNAME")
    password = os.getenv("ONSKESKYEN_PASSWORD")

    if not username or not password:
        logger.error(
            "Please set ONSKESKYEN_USERNAME and ONSKESKYEN_PASSWORD in .env file"
        )
        return

    # Read URLs from file
    wishes_file = Path("wishes.txt")

    with open(wishes_file, "r") as f:
        content = f.read()

    # Extract URLs from the file
    urls = []
    for line in content.split("\n"):
        if "https://www.lego.com/" in line:
            # Extract URL from the line
            start = line.find("https://www.lego.com/")
            end = line.find('"', start)
            if end == -1:
                end = len(line)
            url = line[start:end].strip()
            if url:
                urls.append(url)

    logger.info(f"Found {len(urls)} URLs to add")

    async with async_playwright() as p:
        # Launch browser in headful mode
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to wishlist
        wishlist_url = "https://onskeskyen.dk/da/wishlists/ZhgfNVLL8ydtRJgc"
        await page.goto(wishlist_url)

        # Wait for page to load
        await page.wait_for_load_state("networkidle")

        # Handle cookie consent popup if present
        try:
            # Look for the decline button in cookie popup
            decline_button = await page.query_selector(
                'button#declineButton, button:has-text("Afvis alle")'
            )
            if decline_button:
                logger.info("Cookie consent popup detected, declining cookies...")
                await decline_button.click()
                await page.wait_for_timeout(1000)  # Wait for popup to close
        except Exception as e:
            logger.debug(f"No cookie popup or already handled: {e}")

        # Check if we need to log in (look for login button)
        try:
            # Step 1: Click the initial "Log ind" button
            initial_login_button = await page.query_selector(
                'button.Button__Container-sc-74e86c1a-0:has-text("Log ind")'
            )
            if initial_login_button:
                logger.info("Login required. Starting login process...")
                logger.info("Step 1: Clicking initial 'Log ind' button...")
                await initial_login_button.click()
                await page.wait_for_timeout(1000)

                # Step 2: Click "Fortsæt med e-mail" option
                email_option = await page.query_selector(
                    'div.LoginInitialView__LoginOptionText-sc-c5136ca1-2:has-text("Fortsæt med e-mail")'
                )
                if not email_option:
                    # Try alternative selector
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
                        # Try alternative selector
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
                        # Try alternative selector
                        password_input = await page.query_selector(
                            'input[data-testid="loginPasswordInput"]'
                        )

                    if password_input:
                        logger.info("Step 4: Filling in password...")
                        await password_input.fill(password)
                        await page.wait_for_timeout(500)

                    # Step 5: Click final submit button
                    submit_button = await page.query_selector(
                        'button[data-cy="registerNameNextButton"]:has-text("Log ind")'
                    )
                    if not submit_button:
                        # Try alternative selectors
                        submit_button = await page.query_selector(
                            'button.GradientButton__CustomBtn-sc-b47f63b4-0:has-text("Log ind")'
                        )

                    if submit_button:
                        logger.info("Step 5: Clicking final 'Log ind' button...")
                        await submit_button.click()
                        await page.wait_for_load_state("networkidle")
                        logger.success("Login completed successfully")
                    else:
                        logger.error("Could not find final submit button")
                else:
                    logger.error("Could not find 'Fortsæt med e-mail' option")

                # Navigate to wishlist again if needed
                if wishlist_url not in page.url:
                    logger.info("Navigating back to wishlist...")
                    await page.goto(wishlist_url)
                    await page.wait_for_load_state("networkidle")

                    # Handle cookie popup again if it reappears
                    try:
                        decline_button = await page.query_selector(
                            'button#declineButton, button:has-text("Afvis alle")'
                        )
                        if decline_button:
                            await decline_button.click()
                            await page.wait_for_timeout(1000)
                    except Exception:
                        pass
            else:
                logger.info("No login required or already logged in")
        except Exception as e:
            logger.debug(f"Login process completed with: {e}")

        # Check if we're on the wishlist page
        logger.info("\nChecking if we're on the wishlist page...")
        page_title = await page.title()
        logger.info(f"Page title: {page_title}")

        # Wait a bit for the page to fully load
        await page.wait_for_timeout(2000)

        # Look for the new wish button (plus icon)
        new_wish_button_selector = 'div.NewWishCard__IconContainer-sc-78becbdd-2 img[src="/assets/plusGradient.svg"]'

        # Try to find the new wish button
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
                logger.info("Found 'New Wish' button")
            else:
                logger.error("Could not find 'New Wish' button. Taking screenshot...")
                await page.screenshot(path="debug_screenshot.png")
                logger.info("Screenshot saved as debug_screenshot.png")
                return
        except Exception as e:
            logger.error(f"Error finding new wish button: {e}")
            await page.screenshot(path="debug_screenshot.png")
            logger.info("Screenshot saved as debug_screenshot.png")
            return

        # Add each URL
        for i, url in enumerate(urls, 1):
            try:
                logger.info(f"\nAdding URL {i}/{len(urls)}: {url}")

                # Click the new wish button to open popup
                logger.info("  Clicking 'New Wish' button...")
                await new_wish_button.click()
                await page.wait_for_timeout(1000)  # Wait for popup to appear

                # Fill URL in the popup input field
                url_input_selector = 'input[data-cy="new-wish-input-automatic"][placeholder="Indsæt produktlink"]'
                url_input = await page.wait_for_selector(
                    url_input_selector, timeout=5000
                )

                if url_input:
                    logger.info("  Filling URL in popup...")
                    await url_input.fill(url)
                    await page.wait_for_timeout(1000)

                    # Check for "Spring over" (Skip) popup that sometimes appears
                    try:
                        skip_button = await page.query_selector(
                            'button:has-text("Spring over")'
                        )
                        if skip_button:
                            logger.info(
                                "  'Spring over' popup detected, clicking skip..."
                            )
                            await skip_button.click()
                            await page.wait_for_timeout(500)
                    except Exception:
                        pass  # No skip popup, continue normally
                else:
                    logger.error("  Could not find URL input in popup")
                    continue

                # Click submit button to add the wish
                submit_button_selector = 'button[data-testid="new-wish-form-submit-btn"]:has-text("Tilføj ønske")'
                submit_button = await page.query_selector(submit_button_selector)

                if not submit_button:
                    # Try alternative selector
                    submit_button = await page.query_selector(
                        'button.GradientButton__CustomBtn-sc-b47f63b4-0:has-text("Tilføj ønske")'
                    )

                if submit_button:
                    logger.info("  Clicking 'Tilføj ønske' button...")
                    await submit_button.click()
                    await page.wait_for_timeout(3000)  # Wait for wish to be added
                    logger.success("  ✓ Wish added successfully")
                else:
                    logger.error("  Could not find submit button")
                    # Try to close popup and continue
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(1000)

            except Exception as e:
                logger.error(f"  ✗ Error adding URL {url}: {e}")
                # Try to close any open popup
                try:
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(1000)
                except Exception:
                    pass
                continue

        logger.info(f"Finished adding {len(urls)} URLs to wishlist")

        # Keep browser open for manual verification
        input("Press Enter to close browser...")

        # Close browser properly
        await browser.close()


if __name__ == "__main__":
    asyncio.run(add_urls_to_wishlist())
