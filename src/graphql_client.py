#!/usr/bin/env python3
"""
GraphQL client for making authenticated requests to Onskeskyen/GoWish API
"""

from typing import Any, Dict, Optional

from loguru import logger
from playwright.async_api import Page


class GraphQLClient:
    """Handles GraphQL requests using authenticated browser context"""

    def __init__(self, page: Page):
        self.page = page

    async def execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a GraphQL query using browser context"""
        if not self.page:
            raise Exception("No page available - authentication may have failed")

        payload = {
            "query": query,
            "variables": variables or {},
        }

        logger.debug(f"Making GraphQL request with payload: {payload}")

        # Use page.evaluate to make the fetch request from within the browser context
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

                    // Log current cookies to understand session state
                    console.log('Current cookies:', document.cookie);
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
            if result.get("status") in [401, 403]:
                logger.warning(
                    "Authentication failed - session may have expired. Need re-authentication."
                )
                raise Exception("Authentication expired")
            else:
                raise Exception(
                    f"GraphQL request failed with status {result.get('status')}: {result.get('error', 'Unknown error')}"
                )

        return result.get("data", {})
