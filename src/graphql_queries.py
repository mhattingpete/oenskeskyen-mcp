#!/usr/bin/env python3
"""
GraphQL queries and operations for Onskeskyen/GoWish API
"""

GET_USER_PROFILE_QUERY = """query GetUserProfile {
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

GET_WISHLISTS_PAGINATED_QUERY = """query getWishlistsPaginated($input: PaginationInput, $kinds: [WishlistKind!]) {
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

GET_WISHLIST_PAGE_QUERY = """query getWishlistPage($id: ID!) {
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

GET_WISHLIST_WISHES_QUERY = """query getWishlistWishes($id: ID!, $input: PaginationInput, $sort: WishSortingInput, $filter: SearchTerm, $isLongQuery: Boolean!) {
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

GET_PRODUCT_BY_URL_QUERY = """query productByUrlV2($url: String!, $countryCode: String!) {
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

CREATE_WISH_MUTATION = """mutation createWish($input: CreateWishInput!, $wishlist: ID!, $metadata: MetadataInput!) {
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
