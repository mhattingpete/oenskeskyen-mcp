#!/usr/bin/env python3
"""
Simple test script to demonstrate caching functionality
Run this after starting the API server to see caching in action
"""

import asyncio
import time
import httpx
from datetime import datetime
from loguru import logger


async def test_caching():
    """Test caching behavior with timing measurements"""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        logger.info("🧪 Testing Caching Functionality")
        logger.info("=" * 50)

        # Test 1: Health check
        logger.info("\n1️⃣ Health Check")
        start_time = time.time()
        response = await client.get(f"{base_url}/health")
        duration = time.time() - start_time
        logger.info(f"   Status: {response.status_code}")
        logger.info(f"   Duration: {duration:.3f}s")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   Cache Stats: {data.get('cache_stats', {})}")

        # Test 2: First user profile request (cache miss)
        logger.info("\n2️⃣ User Profile - First Request (Cache Miss)")
        start_time = time.time()
        response = await client.get(f"{base_url}/me")
        duration = time.time() - start_time
        logger.info(f"   Status: {response.status_code}")
        logger.info(f"   Duration: {duration:.3f}s")

        # Test 3: Second user profile request (cache hit)
        logger.info("\n3️⃣ User Profile - Second Request (Cache Hit)")
        start_time = time.time()
        response = await client.get(f"{base_url}/me")
        duration = time.time() - start_time
        logger.info(f"   Status: {response.status_code}")
        logger.info(f"   Duration: {duration:.3f}s (should be faster)")

        # Test 4: Wishlists request (cache miss)
        logger.info("\n4️⃣ Wishlists - First Request (Cache Miss)")
        start_time = time.time()
        response = await client.get(f"{base_url}/wishlists?limit=5")
        duration = time.time() - start_time
        logger.info(f"   Status: {response.status_code}")
        logger.info(f"   Duration: {duration:.3f}s")

        if response.status_code == 200:
            wishlists = response.json()
            if wishlists:
                wishlist_id = wishlists[0]["id"]
                logger.info(f"   Found {len(wishlists)} wishlists")

                # Test 5: Wishlist items (cache miss)
                logger.info("\n5️⃣ Wishlist Items - First Request (Cache Miss)")
                start_time = time.time()
                response = await client.get(
                    f"{base_url}/wishlists/{wishlist_id}/items?limit=3"
                )
                duration = time.time() - start_time
                logger.info(f"   Status: {response.status_code}")
                logger.info(f"   Duration: {duration:.3f}s")

                # Test 6: Same wishlist items (cache hit)
                logger.info("\n6️⃣ Wishlist Items - Second Request (Cache Hit)")
                start_time = time.time()
                response = await client.get(
                    f"{base_url}/wishlists/{wishlist_id}/items?limit=3"
                )
                duration = time.time() - start_time
                logger.info(f"   Status: {response.status_code}")
                logger.info(f"   Duration: {duration:.3f}s (should be faster)")

        # Test 7: Cache statistics
        logger.info("\n7️⃣ Cache Statistics")
        response = await client.get(f"{base_url}/cache/stats")
        if response.status_code == 200:
            stats = response.json()
            cache_stats = stats.get("cache_stats", {})
            logger.info(f"   Total Entries: {cache_stats.get('total_entries', 0)}")
            logger.info(f"   Active Entries: {cache_stats.get('active_entries', 0)}")
            logger.info(
                f"   Memory Usage: {cache_stats.get('memory_usage_mb', 0):.2f} MB"
            )

        logger.success("\n✅ Cache testing completed!")
        logger.info("\n💡 Tips:")
        logger.info("   - Subsequent requests should be faster due to caching")
        logger.info("   - Adding items will invalidate related wishlist cache")
        logger.info("   - Use /cache/stats to monitor cache performance")
        logger.info("   - Use DELETE /cache to clear cache if needed")


if __name__ == "__main__":
    logger.info(f"🕐 Starting cache test at {datetime.now().strftime('%H:%M:%S')}")
    logger.info("📋 Make sure the API server is running at http://localhost:8000")
    logger.info("   Start it with: uv run python start_api.py")

    try:
        asyncio.run(test_caching())
    except httpx.ConnectError:
        logger.error("Could not connect to API server at http://localhost:8000")
        logger.error("   Please start the server first: uv run python start_api.py")
    except Exception as e:
        logger.error(f"Test failed: {e}")
