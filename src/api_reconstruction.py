"""
GoWish API Reconstruction
Based on analysis of onskeskyen.dk

This file documents the reconstructed API structure for https://api.gowish.com
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


@dataclass
class GoWishAPIConfig:
    """Configuration for GoWish API"""

    graphql_endpoint: str = "https://api.gowish.com/graphql"
    auth_endpoint: str = "https://auth.gowish.com"
    token_endpoint: str = "https://auth.gowish.com/oauth/token"

    # OAuth configuration
    client_id: str = os.getenv("GOWISH_CLIENT_ID", "")
    client_secret: str = os.getenv("GOWISH_CLIENT_SECRET", "")
    redirect_uri: str = "http://localhost:8080/callback"

    # OAuth redirect URIs for different locales
    oauth_redirects = {
        "en": "https://api.gowish.com/auth/oauth/redirect",
        "da": "https://onskeskyen.dk/auth/oauth/redirect",
        "no": "https://api.gowish.com/auth/oauth/redirect",
    }


class GoWishAPIClient:
    """Client for interacting with GoWish GraphQL API"""

    def __init__(self, access_token: Optional[str] = None):
        self.config = GoWishAPIConfig()
        self.access_token = access_token
        self.session = requests.Session()

        if access_token:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }
            )

    def graphql_request(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a GraphQL request to the API"""
        payload = {"query": query, "variables": variables or {}}

        response = self.session.post(self.config.graphql_endpoint, json=payload)
        response.raise_for_status()
        return response.json()

    def get_authenticate_url(self, locale: str = "da") -> str:
        """Get OAuth authentication URL for specified locale"""
        redirect_uri = self.config.oauth_redirects.get(
            locale, self.config.oauth_redirects["en"]
        )
        return (
            f"{self.config.auth_endpoint}/oauth/authorize?redirect_uri={redirect_uri}"
        )

    def authenticate_oauth(self) -> str:
        """Authenticate user with OAuth"""
        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "client_credentials",
        }
        response = self.session.post(self.config.auth_endpoint, json=payload)
        response.raise_for_status()
        return response.json()

    def get_user_profile(self) -> dict[str, Any]:
        """Get user profile"""
        return self.graphql_request(
            query=COMMON_QUERIES.get("get_user_profile", ""), variables={}
        )

    def get_wish_lists(self) -> dict[str, Any]:
        """Get wish lists"""
        return self.graphql_request(
            query=COMMON_QUERIES.get("get_wish_lists", ""), variables={}
        )

    def get_wish_list(self, wish_list_id: str) -> dict[str, Any]:
        """Get wish list"""
        return self.graphql_request(
            query=COMMON_QUERIES.get("get_wish_list", ""),
            variables={"id": wish_list_id},
        )


# Common GraphQL queries that might be used based on wish list functionality
COMMON_QUERIES = {
    "get_user_profile": """
    query GetUserProfile {
        user {
            id
            name
            email
            avatar
            locale
        }
    }
    """,
    "get_wish_lists": """
    query GetWishLists {
        wishLists {
            id
            name
            description
            visibility
            createdAt
            updatedAt
            items {
                id
                name
                description
                price
                url
                image
                reserved
            }
        }
    }
    """,
    "create_wish_list": """
    mutation CreateWishList($input: WishListInput!) {
        createWishList(input: $input) {
            id
            name
            description
            visibility
        }
    }
    """,
    "add_wish_item": """
    mutation AddWishItem($wishListId: ID!, $input: WishItemInput!) {
        addWishItem(wishListId: $wishListId, input: $input) {
            id
            name
            description
            price
            url
            image
        }
    }
    """,
}

# Example usage
if __name__ == "__main__":
    # Initialize client (without token for public queries)
    client = GoWishAPIClient()

    print("GoWish API Configuration:")
    print(f"GraphQL Endpoint: {client.config.graphql_endpoint}")
    print(f"Auth Endpoint: {client.config.auth_endpoint}")
    print("OAuth Redirects:")
    for locale, redirect in client.config.oauth_redirects.items():
        print(f"  {locale}: {redirect}")

    print("Authentication")
    client.authenticate_oauth()
    print("Authenticated")

    # Get user profile
    user_profile = client.graphql_request(
        query=COMMON_QUERIES.get("get_user_profile", ""), variables={}
    )
    print(f"User Profile: {user_profile}")
