#!/usr/bin/env python3
"""
Simple in-memory cache service with TTL for API responses
Reduces API calls by caching wishlist and user data
"""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
from loguru import logger


@dataclass
class CacheEntry:
    """Cache entry with data and expiration"""

    data: Any
    created_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = 300  # 5 minutes default

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time


class CacheService:
    """
    Simple in-memory cache with TTL support
    Thread-safe for single-process usage
    """

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

        # Default TTL values (in seconds)
        self.default_ttls = {
            "user_profile": 600,  # 10 minutes - user data changes rarely
            "wishlists": 300,  # 5 minutes - wishlist list changes occasionally
            "wishlist_details": 180,  # 3 minutes - wishlist details change more often
            "wishlist_items": 120,  # 2 minutes - items change frequently
        }

    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from prefix and parameters"""
        # Create deterministic key from parameters
        param_str = json.dumps(kwargs, sort_keys=True, default=str)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{prefix}:{param_hash}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return None

            return entry.data

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL"""
        if ttl is None:
            ttl = 300  # Default 5 minutes

        async with self._lock:
            self._cache[key] = CacheEntry(data=value, ttl_seconds=ttl)

    async def delete(self, key: str) -> None:
        """Delete specific key from cache"""
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed"""
        expired_keys = []
        async with self._lock:
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self._cache)
        expired_count = sum(1 for entry in self._cache.values() if entry.is_expired())

        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_count,
            "expired_entries": expired_count,
            "memory_usage_mb": self._estimate_memory_usage(),
        }

    def _estimate_memory_usage(self) -> float:
        """Rough estimate of memory usage in MB"""
        try:
            import sys

            total_size = sys.getsizeof(self._cache)
            for key, entry in self._cache.items():
                total_size += sys.getsizeof(key)
                total_size += sys.getsizeof(entry)
                total_size += sys.getsizeof(entry.data)
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0

    # Convenience methods for specific data types

    async def get_user_profile(self, user_id: str) -> Optional[Any]:
        """Get cached user profile"""
        key = self._generate_key("user_profile", user_id=user_id)
        return await self.get(key)

    async def set_user_profile(self, user_id: str, data: Any) -> None:
        """Cache user profile data"""
        key = self._generate_key("user_profile", user_id=user_id)
        await self.set(key, data, self.default_ttls["user_profile"])

    async def get_wishlists(
        self, user_id: str, limit: int, cursor: int
    ) -> Optional[Any]:
        """Get cached wishlists"""
        key = self._generate_key(
            "wishlists", user_id=user_id, limit=limit, cursor=cursor
        )
        return await self.get(key)

    async def set_wishlists(
        self, user_id: str, limit: int, cursor: int, data: Any
    ) -> None:
        """Cache wishlists data"""
        key = self._generate_key(
            "wishlists", user_id=user_id, limit=limit, cursor=cursor
        )
        await self.set(key, data, self.default_ttls["wishlists"])

    async def get_wishlist_details(self, wishlist_id: str) -> Optional[Any]:
        """Get cached wishlist details"""
        key = self._generate_key("wishlist_details", wishlist_id=wishlist_id)
        return await self.get(key)

    async def set_wishlist_details(self, wishlist_id: str, data: Any) -> None:
        """Cache wishlist details"""
        key = self._generate_key("wishlist_details", wishlist_id=wishlist_id)
        await self.set(key, data, self.default_ttls["wishlist_details"])

    async def get_wishlist_items(
        self, wishlist_id: str, limit: int, cursor: int
    ) -> Optional[Any]:
        """Get cached wishlist items"""
        key = self._generate_key(
            "wishlist_items", wishlist_id=wishlist_id, limit=limit, cursor=cursor
        )
        return await self.get(key)

    async def set_wishlist_items(
        self, wishlist_id: str, limit: int, cursor: int, data: Any
    ) -> None:
        """Cache wishlist items"""
        key = self._generate_key(
            "wishlist_items", wishlist_id=wishlist_id, limit=limit, cursor=cursor
        )
        await self.set(key, data, self.default_ttls["wishlist_items"])

    async def invalidate_wishlist_cache(self, wishlist_id: str) -> None:
        """Invalidate all cache entries related to a specific wishlist"""
        keys_to_remove = []
        async with self._lock:
            for key in self._cache.keys():
                if (
                    f"wishlist_id={wishlist_id}" in key
                    or f"wishlist_details:{wishlist_id}" in key
                ):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._cache[key]

        logger.info(
            f"🗑️ Invalidated {len(keys_to_remove)} cache entries for wishlist {wishlist_id}"
        )


# Global cache instance
cache_service = CacheService()


async def start_cache_cleanup_task():
    """Background task to clean up expired cache entries"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            removed_count = await cache_service.cleanup_expired()
            if removed_count > 0:
                logger.info(
                    f"🧹 Cache cleanup: removed {removed_count} expired entries"
                )
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying
