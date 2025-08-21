#!/usr/bin/env python3
"""
Reconstructed GoWish/Onskeskyen API Client
Generated from network traffic analysis
"""

from typing import Any, Dict, Optional

import requests


class ReconstructedAPIClient:
    def __init__(
        self,
        session_cookies: Optional[Dict[str, str]] = None,
        auth_token: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ):
        self.session = session or requests.Session()
        self.auth_token = auth_token
        self.use_session_auth = auth_token == "SESSION_AUTH"

        if session_cookies:
            self.session.cookies.update(session_cookies)

    def post_graphql(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        POST /graphql
        Domain: api.gowish.com
        """
        url = "https://api.gowish.com/graphql"

        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def post_graphql_780d0ab0d722afb3c025c911fe319900(
        self, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        POST /graphql/780d0ab0d722afb3c025c911fe319900
        Domain: api.gowish.com
        """
        url = "https://api.gowish.com/graphql/780d0ab0d722afb3c025c911fe319900"

        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def post_graphql_1109a99d57b1f27ecf55b56e9ad106d6(
        self, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        POST /graphql/1109a99d57b1f27ecf55b56e9ad106d6
        Domain: api.gowish.com
        """
        url = "https://api.gowish.com/graphql/1109a99d57b1f27ecf55b56e9ad106d6"

        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def post_token(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        POST /token
        Domain: auth.gowish.com
        """
        url = "https://auth.gowish.com/token"

        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def post_graphql_62e991f5102368fb48587ff160ab2bb6(
        self, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        POST /graphql/62e991f5102368fb48587ff160ab2bb6
        Domain: api.gowish.com
        """
        url = "https://api.gowish.com/graphql/62e991f5102368fb48587ff160ab2bb6"

        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def post_graphql_1972cb8e71ca29a85aaf117a6132391f(
        self, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        POST /graphql/1972cb8e71ca29a85aaf117a6132391f
        Domain: api.gowish.com
        """
        url = "https://api.gowish.com/graphql/1972cb8e71ca29a85aaf117a6132391f"

        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def graphql_request(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute GraphQL query"""
        # You'll need to determine the correct GraphQL endpoint from captured traffic
        graphql_url = (
            "https://api.gowish.com/graphql"  # Update this based on captured data
        )

        payload = {"query": query, "variables": variables or {}}

        # Add required headers from captured traffic
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "x-client-id": "web",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://onskeskyen.dk/",
            "Origin": "https://onskeskyen.dk",
        }

        # Add authorization header if token is available (but not for session auth)
        if self.auth_token and not self.use_session_auth:
            headers["authorization"] = f"Bearer {self.auth_token}"

        response = self.session.post(
            graphql_url, json=payload, headers=headers, allow_redirects=True
        )
        response.raise_for_status()
        return response.json()

    def graphql_getcountrybyip(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL getCountryByIp
        """
        query = """
          query getCountryByIp {
            getCountryByIp
          }
        """

        return self.graphql_request(query, variables)

    def graphql_getwishlistpage(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL getWishlistPage
        """
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
      ...Owner
      __typename
    }
    wishes {
      totalCount
      __typename
    }
    subaccount {
      ...Subaccount
      __typename
    }
    __typename
  }
}

fragment Owner on PublicProfile {
  __typename
  id
  firstName
  lastName
  profileImage
}

fragment Subaccount on SubAccount {
  __typename
  id
  firstName
  lastName
  gender
  birthdate
}"""

        return self.graphql_request(query, variables)

    def graphql_getwishlistwishes(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL getWishlistWishes
        """
        query = """query getWishlistWishes($id: ID!, $input: PaginationInput, $sort: WishSortingInput, $filter: SearchTerm, $isLongQuery: Boolean!) {
  wishlist(id: $id) {
    id
    wishes(input: $input, sort: $sort, filter: $filter) {
      data {
        ...WishItemWithDirectives
        __typename
      }
      totalCount
      nextCursor
      __typename
    }
    __typename
  }
}

fragment WishItemWithDirectives on Wish {
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
    ...Reservation
    __typename
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
    ...ProductRef
    __typename
  }
  __typename
}

fragment Reservation on Reservation {
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

fragment ProductRef on ProductRef {
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
    ...BrandRef
    __typename
  }
}

fragment BrandRef on Brand {
  __typename
  id
  logo
  slug
  isPartner
  hasBabyCategories
  showPriceUpdates
  creatorCommission
}"""

        return self.graphql_request(query, variables)

    def graphql_trackingevent(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL trackingEvent
        """
        query = """mutation trackingEvent($input: [TrackingInputV2!]!) {
  tracking {
    trackV2(input: $input)
    __typename
  }
}"""

        return self.graphql_request(query, variables)

    def graphql_getip(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL GetIP
        """
        query = """query GetIP {
  getCountryByIp
}"""

        return self.graphql_request(query, variables)

    def graphql_isemailavailable(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL IsEmailAvailable
        """
        query = """query IsEmailAvailable($input: EmailInput!) {
  users {
    isEmailAvailable(input: $input)
    isEmailValid(input: $input)
    __typename
  }
}"""

        return self.graphql_request(query, variables)

    def graphql_getme(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL getMe
        """
        query = """query getMe {
  recommendations {
    enrolled
    __typename
  }
  me {
    ...MyProfile
    __typename
  }
}

fragment MyProfile on Me {
  id
  countryCode
  multiBrandId
  email
  pendingEmail
  firstName
  lastName
  languageCode
  profileImage
  isActive
  birthdate
  gender
  featureFlags
  creator {
    audience {
      gender
      maxAge
      minAge
      languageCodes
      __typename
    }
    businessEmail
    categories
    countryCode
    displayName
    id
    profilePicture
    slug
    status
    __typename
  }
  __typename
}"""

        return self.graphql_request(query, variables)

    def graphql_getunseentotalcount(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL getUnseenTotalCount
        """
        query = """query getUnseenTotalCount($kind: NotificationKind) {
  notifications {
    list(kind: $kind) {
      totalCount
      __typename
    }
    __typename
  }
}"""

        return self.graphql_request(query, variables)

    def graphql_getforyoutabscount(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL getForYouTabsCount
        """
        query = """query getForYouTabsCount($country: String!) {
  foryou {
    id
    brands(input: {cursor: 0, limit: 1}) {
      totalCount
      __typename
    }
    eventlists(input: {cursor: 0, limit: 1}) {
      totalCount
      __typename
    }
    giftcards {
      all(country: $country, input: {cursor: 0, limit: 1}) {
        totalCount
        __typename
      }
      __typename
    }
    trendinglists(input: {cursor: 0, limit: 1}) {
      totalCount
      __typename
    }
    __typename
  }
}"""

        return self.graphql_request(query, variables)

    def graphql_recommendationsproductsbylist(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL recommendationsProductsByList
        """
        query = """query recommendationsProductsByList($wishlistId: ID!, $input: PaginationInput, $brands: [ID!], $categories: [String!]) {
  recommendations {
    products {
      fromWishlist(
        wishlistId: $wishlistId
        input: $input
        brands: $brands
        categories: $categories
      ) {
        data {
          id
          currency
          description
          photo
          price
          title
          redirectUrl
          brand {
            id
            name
            logo
            slug
            __typename
          }
          url
          uurl
          countryCode
          originalUrl
          domainName
          __typename
        }
        modelId
        modelType
        nextCursor
        totalCount
        __typename
      }
      __typename
    }
    __typename
  }
}"""

        return self.graphql_request(query, variables)

    def graphql_recommendationsproductsbyaudience(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL recommendationsProductsByAudience
        """
        query = """query recommendationsProductsByAudience($audience: RecommendationAudience!, $input: PaginationInput, $brands: [ID!], $categories: [String!], $doNotSkipBabyCategories: Boolean!) {
  recommendations {
    products {
      fromAudience(
        audience: $audience
        input: $input
        brands: $brands
        categories: $categories
        doNotSkipBabyCategories: $doNotSkipBabyCategories
      ) {
        data {
          id
          currency
          description
          photo
          price
          title
          redirectUrl
          brand {
            id
            name
            logo
            slug
            __typename
          }
          url
          uurl
          countryCode
          originalUrl
          domainName
          __typename
        }
        modelId
        modelType
        nextCursor
        totalCount
        __typename
      }
      __typename
    }
    __typename
  }
}"""

        return self.graphql_request(query, variables)

    def graphql_productbyurlv2(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL productByUrlV2
        """
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

        return self.graphql_request(query, variables)

    def graphql_productmatchv2(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL ProductMatchV2
        """
        query = """query ProductMatchV2($url: String!, $countryCode: String!, $sort: ProductMatchSortingType) {
  products {
    getMatchesByUrl(url: $url, countryCode: $countryCode, sort: $sort) {
      url
      domain
      title
      price
      currencyCode
      countryCode
      logo
      isInStock
      canBeSwapped
      brandId
      stockStatus
      __typename
    }
    __typename
  }
}"""

        return self.graphql_request(query, variables)

    def graphql_getwishlistaccess(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL getWishlistAccess
        """
        query = """query getWishlistAccess($wishlistId: ID!) {
  me {
    id
    __typename
  }
  wishlist(id: $wishlistId) {
    iCollaborate {
      status
      __typename
    }
    owner {
      id
      __typename
    }
    __typename
  }
}"""

        return self.graphql_request(query, variables)

    def graphql_getwishlistspaginated(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL getWishlistsPaginated
        """
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
        ...Owner
        __typename
      }
      subaccount {
        ...Subaccount
        __typename
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
}

fragment Owner on PublicProfile {
  __typename
  id
  firstName
  lastName
  profileImage
}

fragment Subaccount on SubAccount {
  __typename
  id
  firstName
  lastName
  gender
  birthdate
}"""

        return self.graphql_request(query, variables)

    def graphql_createwish(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL createWish
        """
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

        return self.graphql_request(query, variables)

    def graphql_getuserpublicprofile(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL getUserPublicProfile
        """
        query = """query getUserPublicProfile($userId: ID!) {
  user(id: $userId) {
    id
    firstName
    lastName
    profileImage
    coverImage
    isPrivate
    friendship {
      ...Friendship
      __typename
    }
    friends {
      totalCount
      __typename
    }
    wishlists {
      totalCount
      __typename
    }
    wishesCount
    activeWishlists: wishlists(kinds: [My, Shared]) {
      totalCount
      __typename
    }
    __typename
  }
}

fragment Friendship on Friendship {
  __typename
  id
  firstName
  lastName
  profileImage
  friendId
  confirmed
  confirmable
  isPrivate
}"""

        return self.graphql_request(query, variables)

    def graphql_markupdatesasseenonwishlist(
        self, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        GraphQL markUpdatesAsSeenOnWishlist
        """
        query = """mutation markUpdatesAsSeenOnWishlist($withId: ID!) {
  wishlist {
    with(id: $withId) {
      markUpdatesAsSeen
      __typename
    }
    __typename
  }
}"""

        return self.graphql_request(query, variables)


# Example usage:
if __name__ == "__main__":
    # You'll need to provide session cookies from a logged-in browser session
    # These can be extracted from browser dev tools after logging in
    session_cookies = {
        # Add your session cookies here
    }

    client = ReconstructedAPIClient(session_cookies)

    # Example API calls based on discovered endpoints
    try:
        # Add example calls based on your discovered endpoints
        pass
    except Exception as e:
        print(f"Error: {e}")
