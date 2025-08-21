#!/usr/bin/env python3
"""
Authentication service for Onskeskyen/GoWish API
Uses Playwright to maintain authenticated browser session for API requests
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .cache_service import cache_service


class AuthenticationService:
    """
    Service that handles authentication with Onskeskyen using Playwright
    Maintains authenticated browser context for direct API requests
    """

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.authenticated_at: Optional[datetime] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.user_id: Optional[str] = None
        self.captured_headers: Dict[str, str] = {}

    async def authenticate(self) -> None:
        """Perform browser-based authentication and keep browser context active"""
        try:
            playwright = await async_playwright().start()

            # Launch browser in headless mode
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

            # Navigate to login page
            await self.page.goto("https://onskeskyen.dk/da/login")
            await self.page.wait_for_load_state("networkidle")

            # Handle cookie consent if present
            try:
                decline_button = await self.page.query_selector(
                    'button#declineButton, button:has-text("Afvis alle")'
                )
                if decline_button:
                    await decline_button.click()
                    await self.page.wait_for_timeout(1000)
            except Exception:
                pass

            # Perform login
            await self._perform_login(self.page)

            # Navigate to profile to ensure we're authenticated and wait for any GraphQL calls
            await self.page.goto("https://onskeskyen.dk/da/profile")
            await self.page.wait_for_load_state("networkidle")

            # Wait a bit more for any background requests to capture headers
            await self.page.wait_for_timeout(3000)

            # Store captured headers for later use
            self.captured_headers = captured_headers

            self.authenticated_at = datetime.now()
            print("✅ Authentication successful - browser session ready")

        except Exception as e:
            await self._cleanup()
            raise Exception(f"Authentication failed: {e}") from e

    async def _graphql_request(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated GraphQL request using Playwright page evaluation"""
        if not self.page:
            raise Exception("No page available - authentication may have failed")

        # Execute the GraphQL request directly without navigation to avoid losing session
        payload = {
            "query": query,
            "variables": variables or {},
        }

        logger.debug(f"Making GraphQL request with payload: {payload}")

        # Use page.evaluate to make the fetch request from within the browser context
        # This preserves all cookies and session state and extracts any authorization token
        result = await self.page.evaluate(
            """
            async (payload) => {
                try {
                    console.log('Making GraphQL request:', payload);

                    // Try to extract authorization token from local storage or other sources
                    let authToken = null;
                    try {
                        authToken = localStorage.getItem('authToken') ||
                                   sessionStorage.getItem('authToken') ||
                                   localStorage.getItem('token') ||
                                   sessionStorage.getItem('token');
                    } catch (e) {
                        console.log('Could not access storage for auth token:', e);
                    }

                    // Build headers with potential authorization
                    const headers = {
                        'Content-Type': 'application/json',
                        'x-client-id': 'web',
                    };

                    if (authToken) {
                        headers['Authorization'] = authToken.startsWith('Bearer ') ? authToken : `Bearer ${authToken}`;
                        console.log('Using auth token from storage');
                    }

                    console.log('Request headers:', headers);

                    const response = await fetch('https://api.gowish.com/graphql', {
                        method: 'POST',
                        headers: headers,
                        body: JSON.stringify(payload),
                        credentials: 'include'
                    });

                    const data = await response.json();
                    console.log('GraphQL response status:', response.status);
                    console.log('GraphQL response data:', data);

                    return {
                        status: response.status,
                        data: data,
                        headers: Object.fromEntries(response.headers),
                        usedAuthToken: !!authToken
                    };
                } catch (error) {
                    console.error('GraphQL request error:', error);
                    return {
                        status: 500,
                        error: error.message
                    };
                }
            }
            """,
            payload,
        )

        logger.debug(f"GraphQL request result: {result}")

        if result.get("status") != 200:
            # If we get a 401 or other auth error, the session may have expired
            if result.get("status") in [401, 403]:
                logger.warning(
                    "Authentication failed - session may have expired. Attempting re-authentication."
                )
                await self._perform_login(self.page)
                # Retry the request after re-authentication
                return await self._graphql_request(query, variables)
            else:
                raise Exception(
                    f"GraphQL request failed with status {result.get('status')}: {result.get('error', 'Unknown error')}"
                )

        return result.get("data", {})

    async def _perform_login(self, page: Page) -> None:
        """Perform the actual login process using proven working method from main.py"""
        try:
            logger.info("Starting login process using proven working method...")

            # Navigate to the wishlist page to trigger login flow
            wishlist_url = "https://onskeskyen.dk/da/wishlists/ZhgfNVLL8ydtRJgc"
            await page.goto(wishlist_url)
            await page.wait_for_load_state("networkidle")

            # Check if we need to log in (look for login button)
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
                        await email_input.fill(self.username)
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
                        await password_input.fill(self.password)
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

                # Stay on the current page and wait for authentication to be established
                logger.info(
                    "Login completed, waiting for authentication to be established..."
                )
                await page.wait_for_timeout(2000)
            else:
                logger.info("No login required or already logged in")
                # Navigate to profile to establish authenticated session
                await page.goto("https://onskeskyen.dk/da/profile")
                await page.wait_for_load_state("networkidle")

        except Exception as e:
            logger.error(f"Login process failed: {e}")
            # Take screenshot on error for debugging
            try:
                await page.screenshot(path="login_error.png")
                logger.info("Screenshot saved as login_error.png")
            except Exception:
                pass
            raise Exception(f"Login process failed: {e}") from e

    async def _cleanup(self) -> None:
        """Clean up browser resources"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception:
            pass  # Ignore cleanup errors

    def is_authenticated(self) -> bool:
        """Check if the service is currently authenticated"""
        if not self.authenticated_at or not self.page:
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
        query = """query GetUserProfile {
            me {
                id
                firstName
                lastName
                email
                profileImage
                languageCode
                countryCode
                isActive
            }
        }"""

        profile_data = await self._graphql_request(query)

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
        query = """query getWishlistsPaginated($input: PaginationInput, $kinds: [WishlistKind!]) {
  wishlists(input: $input, kinds: $kinds) {
    __typename
    nextCursor
    totalCount
    data {
      newUpdates
      lastUpdateSeenAt
      iFollow
      id
      title
      accessLevel
      eventType
      expires
      coverPhoto
      description
      owner {
        __typename
        id
        firstName
        lastName
        profileImage
      }
      subaccount {
        __typename
        id
        firstName
        lastName
        gender
        birthdate
      }
      collaborators {
        totalCount
        data {
          id
          firstName
          collaboration {
            status
            __typename
          }
          __typename
        }
        __typename
      }
      followers {
        totalCount
        data {
          id
          __typename
        }
        __typename
      }
      wishes(input: {cursor: 0, limit: 1}) {
        data {
          id
          photos
          title
          description
          price
          currency
          __typename
        }
        totalCount
        __typename
      }
      reservationOptions {
        ownerCanReserve
        reservedWishesCount
        __typename
      }
      __typename
    }
  }
}"""

        variables = {
            "input": {"cursor": cursor, "limit": limit},
            "kinds": ["My", "Shared"],
        }

        wishlists_data = await self._graphql_request(query, variables)

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
        query = """query getWishlistPage($id: ID!) {
  wishlist(id: $id) {
    newUpdates
    lastUpdateSeenAt
    lastUpdatedAt
    iFollow
    id
    title
    accessLevel
    eventType
    expires
    archived
    coverPhoto
    description
    reservationOptions {
      ownerCanReserve
      reservedWishesCount
      __typename
    }
    iCollaborate {
      status
      __typename
    }
    followers {
      totalCount
      __typename
    }
    collaborators(input: {cursor: 0, limit: 10}) {
      data {
        id
        firstName
        lastName
        profileImage
        collaboration {
          status
          __typename
        }
        __typename
      }
      totalCount
      __typename
    }
    owner {
      __typename
      id
      firstName
      lastName
      profileImage
    }
    wishes {
      totalCount
      __typename
    }
    subaccount {
      __typename
      id
      firstName
      lastName
      gender
      birthdate
    }
    __typename
  }
}"""

        variables = {"id": wishlist_id}
        details_data = await self._graphql_request(query, variables)

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
        query = """query getWishlistWishes($id: ID!, $input: PaginationInput, $sort: WishSortingInput, $filter: SearchTerm, $isLongQuery: Boolean!) {
  wishlist(id: $id) {
    id
    wishes(input: $input, sort: $sort, filter: $filter) {
      data {
        updatedAt
        description
        id
        price
        quantity
        photos
        index
        title
        url
        currency
        labels
        redirectUrl
        iPurchasedIt
        reservations {
          __typename
          quantity
          reservedBy {
            __typename
            id
            firstName
            lastName
            profileImage
          }
        }
        next @include(if: $isLongQuery) {
          id
          index
          __typename
        }
        prev @include(if: $isLongQuery) {
          id
          index
          __typename
        }
        productRef {
          __typename
          id
          uurl
          countryCode
          originalUrl
          domainName
          price
          currency
          crossedOutPrice
          inStock
          displayPrice
          brand {
            __typename
            id
            logo
            slug
            isPartner
            hasBabyCategories
            showPriceUpdates
            creatorCommission
          }
        }
        __typename
      }
      totalCount
      nextCursor
      __typename
    }
    __typename
  }
}"""

        variables = {
            "id": wishlist_id,
            "input": {"cursor": cursor, "limit": limit},
            "sort": {"field": "index", "direction": "ASC"},
            "filter": None,
            "isLongQuery": True,
        }

        items_data = await self._graphql_request(query, variables)

        # Cache the result
        await cache_service.set_wishlist_items(wishlist_id, limit, cursor, items_data)

        return items_data

    async def get_product_by_url(
        self, url: str, country_code: str = "DK"
    ) -> Dict[str, Any]:
        """Get product metadata from URL using productByUrlV2 query"""
        await self.refresh_authentication()

        query = """query productByUrlV2($url: String!, $countryCode: String!) {
  products {
    getByUrlV2(url: $url, countryCode: $countryCode) {
      id
      currency
      description
      price
      title
      ... on ExternalProduct {
        imageUrls
        originalUrl
        domainName
        uurl
        countryCode
        creatorCommission
        brand {
          id
          logo
          name
          website
          creatorCommission
          __typename
        }
        __typename
      }
      ... on ParentProduct {
        photo
        url
        country: countryCode
        productMatches(countryCode: $countryCode) {
          countryCode
          currencyCode
          domain
          price
          url
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}"""

        variables = {"url": url, "countryCode": country_code}
        result = await self._graphql_request(query, variables)
        
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
                if (product_data.get("data") and 
                    product_data["data"].get("products") and 
                    product_data["data"]["products"].get("getByUrlV2")):
                    
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
                "uurl": product_metadata.get("uurl")
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
        query = """mutation createWish($input: CreateWishInput!, $wishlist: ID!, $metadata: MetadataInput!) {
  wish {
    create(input: $input, wishlist: $wishlist, metadata: $metadata) {
      id
      title
      price
      quantity
      description
      photos
      wishlist {
        owner {
          id
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}"""

        variables = {
            "input": wish_input,
            "wishlist": wishlist_id,
            "metadata": {},
        }

        result = await self._graphql_request(query, variables)
        
        # Debug logging to understand the response structure
        logger.info(f"create_wish GraphQL response: {result}")
        
        # Let's capture a real metadata example by navigating to a wishlist and observing the network
        if False:  # Disable this for now, but keep for reference
            await self._capture_real_metadata_example(wishlist_id)

        # Invalidate related cache entries since we added a new item
        await cache_service.invalidate_wishlist_cache(wishlist_id)

        return result

    async def _capture_real_metadata_example(self, wishlist_id: str):
        """Navigate to wishlist page and capture real metadata from network traffic"""
        try:
            logger.info(f"Navigating to wishlist {wishlist_id} to capture real metadata...")
            
            # Navigate to the specific wishlist page
            await self.page.goto(f"https://onskeskyen.dk/wishlists/{wishlist_id}")
            await self.page.wait_for_load_state("networkidle")
            
            # Setup network listener to capture GraphQL requests
            captured_requests = []
            
            def capture_request(request):
                if "graphql" in request.url and request.method == "POST":
                    captured_requests.append({
                        "url": request.url,
                        "headers": dict(request.headers),
                        "post_data": request.post_data
                    })
            
            self.page.on("request", capture_request)
            
            logger.info("Setup complete. You can now manually add an item to capture the real metadata...")
            # In a real scenario, we would wait for the user to add an item or programmatically trigger it
            # For now, we'll just log what we need to do
            
            # Remove listener
            self.page.remove_listener("request", capture_request)
            
            # Log any captured requests
            for req in captured_requests:
                logger.info(f"Captured GraphQL request: {req}")
                
        except Exception as e:
            logger.error(f"Error capturing real metadata: {e}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup()
