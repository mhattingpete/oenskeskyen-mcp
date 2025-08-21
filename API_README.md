# Onskeskyen API Gateway

A FastAPI-based REST API gateway that provides programmatic access to Onskeskyen/GoWish wishlist operations.

## Features

- ✅ **User Profile**: Get current user information
- ✅ **List Wishlists**: Get all user wishlists with pagination  
- ✅ **Wishlist Details**: Get detailed information about a specific wishlist
- ✅ **List Items**: Get items from a specific wishlist
- ✅ **Add Items**: Add new items to wishlists via URL with automatic metadata extraction
- ✅ **Product Metadata**: Extract product information from URLs for preview
- ✅ **Smart Caching**: In-memory caching with TTL to reduce API calls
- ⏳ **Delete Items**: Planned (delete API endpoint not yet captured)

## 🚀 **NEW: Automatic Product Metadata Extraction**

The API now supports **automatic product metadata extraction** from URLs:

- **🎯 Smart Detection**: Automatically extracts title, description, price, and images from product URLs
- **🌍 Multi-Store Support**: Works with LEGO, fashion retailers, and many other e-commerce sites
- **💰 Currency Auto-Detection**: Sets appropriate currency based on product region
- **📸 Image Processing**: Downloads and processes product images automatically
- **🔄 Graceful Fallback**: Falls back to manual values if extraction fails
- **⚡ Performance**: Much faster than browser automation - direct API calls only

### Example: Add a LEGO set with just the URL
```bash
curl -X POST "http://localhost:8000/wishlists/YOUR_WISHLIST_ID/items" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.lego.com/en-us/product/millennium-falcon-75375"}'
```
**Result**: Automatically extracts "Millennium Falcon™ 75375", $84.99, description, and product image!

## Quick Start

### 1. Environment Setup

Create a `.env` file with your Onskeskyen credentials:

```bash
# Required - Onskeskyen login credentials
ONSKESKYEN_USERNAME=your-email@example.com
ONSKESKYEN_PASSWORD=your-password

# Optional - Server configuration
HOST=0.0.0.0
PORT=8000
RELOAD=true
LOG_LEVEL=info
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Start the API Server

```bash
# Using make (recommended)
make api

# Or directly with uv
uv run python start_api.py
```

The API will be available at:
- **API Endpoints**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
Authentication is handled automatically using environment variables. The service performs browser-based login on startup and maintains session cookies.

### Core Endpoints

| Method | Endpoint | Description | Cache TTL |
|--------|----------|-------------|-----------|
| `GET` | `/health` | Health check, authentication status, and cache stats | No cache |
| `GET` | `/me` | Get current user profile | 10 min |
| `GET` | `/wishlists` | Get all user wishlists with pagination | 5 min |
| `GET` | `/wishlists/{id}` | Get specific wishlist details | 3 min |
| `GET` | `/wishlists/{id}/items` | Get items from a wishlist | 2 min |
| `POST` | `/wishlists/{id}/items` | Add new item to wishlist with automatic metadata | Invalidates cache |
| `GET` | `/products/metadata` | Get product metadata from URL | No cache |
| `DELETE` | `/wishlists/{id}/items/{item_id}` | Delete item (not implemented) | - |
| `GET` | `/cache/stats` | Get cache statistics | No cache |
| `DELETE` | `/cache` | Clear all cache entries | No cache |

## Detailed Endpoint Documentation

### 1. Health Check

**`GET /health`**

Returns API health status, authentication state, and cache statistics.

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-20T12:16:31.939100",
  "authenticated": true,
  "cache_stats": {
    "total_entries": 3,
    "active_entries": 3,
    "expired_entries": 0,
    "memory_usage_mb": 0.001
  }
}
```

### 2. User Profile

**`GET /me`**

Get current authenticated user profile information.

**Response (200):**
```json
{
  "id": "F99AhwjphaZLSpNZ",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "language_code": "da",
  "country_code": "DK",
  "profile_image": "https://img.gowish.com/uploads/images/avatar/...",
  "is_active": true,
  "created_at": null
}
```

**Error Responses:**
- `503 Service Unavailable`: Authentication service not initialized
- `500 Internal Server Error`: Failed to get user profile

### 3. List Wishlists

**`GET /wishlists`**

Get all user wishlists with pagination support.

**Query Parameters:**
- `limit` (integer, 1-100, default: 50): Number of wishlists per page
- `cursor` (integer, ≥0, default: 0): Pagination cursor

**Example Request:**
```bash
curl "http://localhost:8000/wishlists?limit=10&cursor=0"
```

**Response (200):**
```json
[
  {
    "id": "j2pNAwngVECaYrSd",
    "title": "My Wishlist",
    "description": null,
    "access_level": "Public",
    "event_type": "EVENT_PERSONAL_SHOPPING",
    "cover_photo": "https://img.gowish.com/gowish-prod-storage/files/...",
    "owner": {
      "id": "F99AhwjphaZLSpNZ",
      "first_name": "John",
      "last_name": "Doe",
      "profile_image": "https://img.gowish.com/uploads/images/avatar/..."
    },
    "wishes_count": 5,
    "collaborators_count": 0,
    "followers_count": 10,
    "archived": false,
    "expires": null,
    "last_updated_at": "2025-08-20T03:43:10.484000Z",
    "new_updates": false
  }
]
```

**Error Responses:**
- `422 Validation Error`: Invalid query parameters (limit > 100 or < 1)
- `500 Internal Server Error`: Failed to get wishlists

### 4. Get Wishlist Details

**`GET /wishlists/{wishlist_id}`**

Get detailed information about a specific wishlist.

**Path Parameters:**
- `wishlist_id` (string): The wishlist ID

**Example Request:**
```bash
curl "http://localhost:8000/wishlists/j2pNAwngVECaYrSd"
```

**Response (200):**
```json
{
  "id": "j2pNAwngVECaYrSd",
  "title": "My Wishlist",
  "description": null,
  "access_level": "Public",
  "event_type": "EVENT_PERSONAL_SHOPPING",
  "cover_photo": "https://img.gowish.com/gowish-prod-storage/files/...",
  "owner": {
    "id": "F99AhwjphaZLSpNZ",
    "first_name": "John",
    "last_name": "Doe",
    "profile_image": "https://img.gowish.com/uploads/images/avatar/..."
  },
  "wishes_count": 5,
  "collaborators_count": 0,
  "followers_count": 10,
  "archived": false,
  "expires": null,
  "last_updated_at": "2025-08-20T03:43:10.484000Z",
  "new_updates": false
}
```

**Error Responses:**
- `404 Not Found`: Wishlist not found
- `500 Internal Server Error`: Failed to get wishlist

### 5. Get Wishlist Items

**`GET /wishlists/{wishlist_id}/items`**

Get items from a specific wishlist with pagination.

**Path Parameters:**
- `wishlist_id` (string): The wishlist ID

**Query Parameters:**
- `limit` (integer, 1-100, default: 24): Number of items per page
- `cursor` (integer, ≥0, default: 0): Pagination cursor

**Example Request:**
```bash
curl "http://localhost:8000/wishlists/j2pNAwngVECaYrSd/items?limit=5&cursor=0"
```

**Response (200):**
```json
[
  {
    "id": "vyXRPMvOvea4R2mD",
    "title": "LEGO Product",
    "description": "A great LEGO set for kids...",
    "price": "252",
    "currency": "DKK",
    "quantity": 1,
    "url": "https://www.lego.com/da-dk/product/...",
    "redirect_url": "https://api.gowish.com/click?data=...",
    "photos": ["https://img.gowish.com/gowish-prod-storage/files/..."],
    "labels": [],
    "index": 0,
    "updated_at": "2025-08-18T11:58:45.109000Z",
    "purchased": false
  }
]
```

**Error Responses:**
- `422 Validation Error`: Invalid query parameters
- `500 Internal Server Error`: Failed to get wishlist items

### 6. Add Wishlist Item

**`POST /wishlists/{wishlist_id}/items`**

Add a new item to a wishlist by URL with automatic metadata extraction.

**Path Parameters:**
- `wishlist_id` (string): The wishlist ID

**Request Body:**
```json
{
  "url": "https://www.example.com/product",
  "title": "Custom Item Title",
  "description": "Optional description",
  "price": 99.99,
  "quantity": 1,
  "use_url_metadata": true
}
```

**Required Fields:**
- `url` (string): Product URL

**Optional Fields:**
- `title` (string): Custom title (overrides automatic extraction)
- `description` (string): Item description (overrides automatic extraction)
- `price` (number): Item price (overrides automatic extraction)
- `quantity` (integer, default: 1): Quantity
- `use_url_metadata` (boolean, default: true): Automatically extract metadata from URL

**Automatic Metadata Extraction:**
When `use_url_metadata` is `true` (default), the API automatically:
- ✅ Extracts product title, description, and price from the URL
- ✅ Downloads and processes product images
- ✅ Sets appropriate currency based on product region
- ✅ Links to original product page
- ✅ Falls back to provided values if extraction fails

**Example Request (Automatic Metadata):**
```bash
curl -X POST "http://localhost:8000/wishlists/j2pNAwngVECaYrSd/items" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://wardrobe19.com/collections/ss25-sale/products/prequel-s1006-stand-up-collar-shirt-natural",
    "use_url_metadata": true
  }'
```

**Example Request (Manual Override):**
```bash
curl -X POST "http://localhost:8000/wishlists/j2pNAwngVECaYrSd/items" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.lego.com/en-us/product/millennium-falcon-75375",
    "title": "My Custom Title",
    "description": "My custom description",
    "price": 120.00,
    "use_url_metadata": true
  }'
```

**Response (200):**
```json
{
  "success": true,
  "message": "Wishlist item added successfully",
  "item": {
    "id": "s3C2bRa3aNbagJRK",
    "title": "Millennium Falcon™ 75375 | Star Wars™ | Buy online at the Official LEGO® Shop US",
    "description": "Collectible LEGO® Star Wars™ vehicle set for adults",
    "price": "84.99",
    "currency": "USD",
    "quantity": 1,
    "url": "https://www.lego.com/en-us/product/millennium-falcon-75375",
    "redirect_url": "https://api.gowish.com/click?data=...",
    "photos": ["https://img.gowish.com/gowish-prod-storage/files/..."],
    "labels": [],
    "index": 0,
    "updated_at": "2025-08-21T04:35:05.118000Z",
    "purchased": false
  }
}
```

**Error Responses:**
- `422 Validation Error`: Missing required fields or invalid data
- `500 Internal Server Error`: Failed to add wishlist item

### 7. Get Product Metadata

**`GET /products/metadata`**

Extract product metadata from a URL without adding it to a wishlist. Useful for previewing product information before adding.

**Query Parameters:**
- `url` (string, required): Product URL to extract metadata from
- `country_code` (string, default: "DK"): Country code for price/currency localization

**Example Request:**
```bash
curl "http://localhost:8000/products/metadata?url=https://wardrobe19.com/collections/ss25-sale/products/prequel-s1006-stand-up-collar-shirt-natural&country_code=DK"
```

**Response (200) - Success:**
```json
{
  "success": true,
  "product": {
    "id": "d2FyZHJvYmUxOS5jb20vY29sbGVjdGlvbnMvc3MyNS1zYWxlL3Byb2R1Y3RzL3ByZXF1ZWwtczEwMDYtc3RhbmQtdXAtY29sbGFyLXNoaXJ0LW5hdHVyYWx7aWQ6OnYxfURL",
    "currency": "EUR",
    "description": "We're excited to bring Japanese brand Prequel to Wardrobe 19!...",
    "price": 159.95,
    "title": "Prequel, S1006 Stand-Up Collar Shirt, Natural",
    "imageUrls": ["https://img.gowish.com/scrapers/v1/image/url?targetUrl=..."],
    "originalUrl": "https://wardrobe19.com/collections/ss25-sale/products/prequel-s1006-stand-up-collar-shirt-natural",
    "domainName": "wardrobe19.com",
    "uurl": "wardrobe19.com/collections/ss25-sale/products/prequel-s1006-stand-up-collar-shirt-natural",
    "countryCode": "DK",
    "brand": {
      "id": "brandId123",
      "name": "Brand Name",
      "website": "https://brand.com/"
    }
  },
  "raw_response": {
    "data": { /* Full GraphQL response */ }
  }
}
```

**Response (200) - No Metadata Found:**
```json
{
  "success": false,
  "message": "No product metadata found for this URL",
  "raw_response": {
    "data": { /* GraphQL response */ }
  }
}
```

**Supported Websites:**
The metadata extraction works with major e-commerce sites including:
- ✅ LEGO (lego.com)
- ✅ Wardrobe19 (wardrobe19.com)
- ✅ And many other online stores

**Error Responses:**
- `422 Validation Error`: Missing or invalid URL parameter
- `500 Internal Server Error`: Failed to extract metadata

### 8. Delete Wishlist Item

**`DELETE /wishlists/{wishlist_id}/items/{item_id}`**

Delete an item from a wishlist. **Currently not implemented.**

**Response (501):**
```json
{
  "detail": "Delete functionality not yet implemented - delete API endpoint not captured"
}
```

### 9. Cache Statistics

**`GET /cache/stats`**

Get current cache statistics and performance metrics.

**Response (200):**
```json
{
  "cache_stats": {
    "total_entries": 5,
    "active_entries": 4,
    "expired_entries": 1,
    "memory_usage_mb": 0.002
  },
  "timestamp": "2025-08-20T12:23:20.241802"
}
```

### 10. Clear Cache

**`DELETE /cache`**

Clear all cached data to force fresh API calls.

**Response (200):**
```json
{
  "message": "Cache cleared successfully",
  "timestamp": "2025-08-20T12:23:20.241802"
}
```

## Quick Examples

### Get User Profile
```bash
curl http://localhost:8000/me
```

### List First 5 Wishlists
```bash
curl "http://localhost:8000/wishlists?limit=5"
```

### Get Specific Wishlist Details
```bash
curl "http://localhost:8000/wishlists/j2pNAwngVECaYrSd"
```

### Get Items from a Wishlist
```bash
curl "http://localhost:8000/wishlists/j2pNAwngVECaYrSd/items?limit=10"
```

### Add Item with Automatic Metadata
```bash
curl -X POST "http://localhost:8000/wishlists/j2pNAwngVECaYrSd/items" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.lego.com/en-us/product/millennium-falcon-75375",
    "use_url_metadata": true
  }'
```

### Preview Product Metadata
```bash
curl "http://localhost:8000/products/metadata?url=https://wardrobe19.com/collections/ss25-sale/products/prequel-s1006-stand-up-collar-shirt-natural"
```

### Add Item with Custom Override
```bash
curl -X POST "http://localhost:8000/wishlists/j2pNAwngVECaYrSd/items" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.lego.com/da-dk/product/road-plates-60304",
    "title": "My Custom Title",
    "description": "Custom description",
    "quantity": 2,
    "use_url_metadata": true
  }'
```

### Check Health and Cache Status
```bash
curl http://localhost:8000/health
```

### Clear Cache for Fresh Data
```bash
curl -X DELETE http://localhost:8000/cache
```

## HTTP Status Codes

| Code | Description | Common Scenarios |
|------|-------------|------------------|
| `200` | OK | Successful GET/POST/DELETE requests |
| `404` | Not Found | Wishlist ID doesn't exist |
| `422` | Validation Error | Invalid query params, missing required fields |
| `500` | Internal Server Error | API call failed, authentication expired |
| `501` | Not Implemented | Delete item endpoint |
| `503` | Service Unavailable | Authentication service not initialized |

## Validation Rules

### Query Parameters
- **limit**: Must be between 1 and 100 (inclusive)
- **cursor**: Must be ≥ 0

### Request Body (Add Item)
- **url** (required): Must be a valid URL string
- **title** (optional): String, custom item title (overrides extracted metadata)
- **description** (optional): String, item description (overrides extracted metadata)
- **price** (optional): Number, item price (overrides extracted metadata)
- **quantity** (optional): Integer ≥ 1, defaults to 1
- **use_url_metadata** (optional): Boolean, defaults to true (automatically extract product info)

## Architecture

The API gateway consists of:

1. **FastAPI Application** (`app.py`) - REST API endpoints and routing
2. **Authentication Service** (`auth_service.py`) - Browser-based login and session management
3. **Reconstructed API Client** (`reconstructed_api_client.py`) - GraphQL API wrapper
4. **Cache Service** (`cache_service.py`) - In-memory caching with TTL
5. **Pydantic Models** (`models.py`) - Request/response validation and serialization

## Caching Strategy

The API implements intelligent caching to reduce load on the upstream GoWish API:

### Cache TTL Values
- **User Profile**: 10 minutes (rarely changes)
- **Wishlists List**: 5 minutes (changes occasionally)
- **Wishlist Details**: 3 minutes (moderate change frequency)
- **Wishlist Items**: 2 minutes (changes frequently)

### Cache Behavior
- **Cache Miss**: Data fetched from API and cached
- **Cache Hit**: Data served from memory (faster response)
- **Cache Invalidation**: Adding items clears related wishlist cache
- **Auto Cleanup**: Expired entries removed every 5 minutes

### Cache Management
```bash
# Get cache statistics
curl http://localhost:8000/cache/stats

# Clear all cache (force fresh data)
curl -X DELETE http://localhost:8000/cache
```

## Error Handling

The API provides structured error responses:

```json
{
  "detail": "Error description",
  "status_code": 500
}
```

Common error scenarios:
- `503 Service Unavailable`: Authentication service not initialized
- `500 Internal Server Error`: API call failed or authentication expired
- `501 Not Implemented`: Delete functionality not yet available
- `422 Validation Error`: Invalid request data

## Development

### Running in Development Mode
```bash
# Enable auto-reload on code changes
RELOAD=true make api

# Or with uv directly
RELOAD=true uv run python start_api.py
```

### Testing
```bash
# Test API endpoints interactively
# Visit http://localhost:8000/docs

# Test caching performance
make test-cache
```

## Limitations

- **Delete Items**: Not yet implemented (requires capturing delete API endpoint)
- **Session Management**: Sessions expire after 8 hours and require restart
- **Rate Limiting**: No built-in rate limiting (consider adding for production)
- **Authentication**: Single-user mode only (uses credentials from environment)