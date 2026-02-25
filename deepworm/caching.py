"""Advanced caching utilities for document processing.

Provides LRU cache, TTL cache, tiered caching, cache statistics,
serialization, and cache warming for research operations.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class EvictionPolicy(Enum):
    """Cache eviction policies."""

    LRU = "lru"        # Least Recently Used
    LFU = "lfu"        # Least Frequently Used
    FIFO = "fifo"      # First In, First Out
    TTL = "ttl"        # Time To Live (expire oldest)


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""

    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None  # seconds

    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl

    @property
    def age(self) -> float:
        """Age in seconds since creation."""
        return time.time() - self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "ttl": self.ttl,
            "is_expired": self.is_expired,
            "age": round(self.age, 2),
        }


@dataclass
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expired: int = 0
    sets: int = 0
    deletes: int = 0

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate

    def reset(self) -> None:
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expired = 0
        self.sets = 0
        self.deletes = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expired": self.expired,
            "sets": self.sets,
            "deletes": self.deletes,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 4),
        }


class Cache:
    """In-memory cache with configurable eviction policy.

    Supports LRU, LFU, FIFO eviction and optional TTL per entry.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        policy: EvictionPolicy = EvictionPolicy.LRU,
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.policy = policy
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats()

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def stats(self) -> CacheStats:
        return self._stats

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache."""
        entry = self._entries.get(key)
        if entry is None:
            self._stats.misses += 1
            return default

        if entry.is_expired:
            self._entries.pop(key, None)
            self._stats.expired += 1
            self._stats.misses += 1
            return default

        # Update access metadata
        entry.last_accessed = time.time()
        entry.access_count += 1

        if self.policy == EvictionPolicy.LRU:
            self._entries.move_to_end(key)

        self._stats.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a value in cache."""
        if key in self._entries:
            self._entries.pop(key)

        ttl = ttl if ttl is not None else self.default_ttl

        if len(self._entries) >= self.max_size:
            self._evict()

        self._entries[key] = CacheEntry(
            key=key,
            value=value,
            ttl=ttl,
        )
        self._stats.sets += 1

    def delete(self, key: str) -> bool:
        """Delete a key from cache. Returns True if found."""
        if key in self._entries:
            del self._entries[key]
            self._stats.deletes += 1
            return True
        return False

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        entry = self._entries.get(key)
        if entry is None:
            return False
        if entry.is_expired:
            self._entries.pop(key, None)
            self._stats.expired += 1
            return False
        return True

    def clear(self) -> int:
        """Clear all entries. Returns count of removed entries."""
        count = len(self._entries)
        self._entries.clear()
        return count

    def keys(self) -> List[str]:
        """Return all non-expired keys."""
        self._purge_expired()
        return list(self._entries.keys())

    def values(self) -> List[Any]:
        """Return all non-expired values."""
        self._purge_expired()
        return [e.value for e in self._entries.values()]

    def items(self) -> List[Tuple[str, Any]]:
        """Return all non-expired (key, value) pairs."""
        self._purge_expired()
        return [(k, e.value) for k, e in self._entries.items()]

    def get_entry(self, key: str) -> Optional[CacheEntry]:
        """Get the full cache entry with metadata."""
        entry = self._entries.get(key)
        if entry and entry.is_expired:
            self._entries.pop(key, None)
            self._stats.expired += 1
            return None
        return entry

    def _evict(self) -> None:
        """Evict one entry based on policy."""
        if not self._entries:
            return

        if self.policy == EvictionPolicy.LRU:
            # Remove least recently used (first in OrderedDict)
            self._entries.popitem(last=False)
        elif self.policy == EvictionPolicy.LFU:
            # Remove least frequently used
            min_key = min(self._entries, key=lambda k: self._entries[k].access_count)
            self._entries.pop(min_key)
        elif self.policy == EvictionPolicy.FIFO:
            self._entries.popitem(last=False)
        elif self.policy == EvictionPolicy.TTL:
            # Remove oldest entry
            oldest_key = min(self._entries, key=lambda k: self._entries[k].created_at)
            self._entries.pop(oldest_key)

        self._stats.evictions += 1

    def _purge_expired(self) -> None:
        """Remove all expired entries."""
        expired_keys = [k for k, e in self._entries.items() if e.is_expired]
        for key in expired_keys:
            self._entries.pop(key)
            self._stats.expired += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "size": self.size,
            "max_size": self.max_size,
            "policy": self.policy.value,
            "default_ttl": self.default_ttl,
            "stats": self._stats.to_dict(),
        }


class TieredCache:
    """Multi-tier caching (e.g., L1 fast/small + L2 slow/large).

    Checks tiers in order, promotes entries to higher tiers on access.
    """

    def __init__(self, tiers: Optional[List[Cache]] = None):
        if tiers is None:
            # Default: L1 small fast, L2 larger slow
            tiers = [
                Cache(max_size=100, policy=EvictionPolicy.LRU),
                Cache(max_size=10000, policy=EvictionPolicy.LRU),
            ]
        self._tiers = tiers

    @property
    def tier_count(self) -> int:
        return len(self._tiers)

    def get(self, key: str, default: Any = None) -> Any:
        """Get from first available tier, promoting to L1."""
        for i, tier in enumerate(self._tiers):
            value = tier.get(key)
            if value is not None:
                # Promote to higher tiers
                for j in range(i):
                    self._tiers[j].set(key, value)
                return value
        return default

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set in all tiers."""
        for tier in self._tiers:
            tier.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete from all tiers."""
        deleted = False
        for tier in self._tiers:
            if tier.delete(key):
                deleted = True
        return deleted

    def clear(self) -> int:
        """Clear all tiers."""
        total = 0
        for tier in self._tiers:
            total += tier.clear()
        return total

    def stats(self) -> List[Dict[str, Any]]:
        """Get stats from all tiers."""
        return [tier.to_dict() for tier in self._tiers]


class ComputeCache:
    """Cache that computes values on miss via a loader function."""

    def __init__(
        self,
        loader: Callable[[str], Any],
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
    ):
        self._loader = loader
        self._cache = Cache(max_size=max_size, default_ttl=default_ttl)

    def get(self, key: str) -> Any:
        """Get from cache; compute and store on miss."""
        value = self._cache.get(key)
        if value is not None:
            return value
        # Compute
        value = self._loader(key)
        if value is not None:
            self._cache.set(key, value)
        return value

    def invalidate(self, key: str) -> bool:
        return self._cache.delete(key)

    def clear(self) -> int:
        return self._cache.clear()

    @property
    def stats(self) -> CacheStats:
        return self._cache.stats

    @property
    def size(self) -> int:
        return self._cache.size


def cache_key(*args: Any, **kwargs: Any) -> str:
    """Generate a deterministic cache key from arguments."""
    parts = [str(a) for a in args]
    for k in sorted(kwargs):
        parts.append(f"{k}={kwargs[k]}")
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def memoize(
    max_size: int = 256,
    ttl: Optional[float] = None,
) -> Callable:
    """Decorator to memoize function results.

    Usage:
        @memoize(max_size=100, ttl=3600)
        def expensive_function(x):
            ...
    """

    def decorator(func: Callable) -> Callable:
        cache = Cache(max_size=max_size, default_ttl=ttl)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = cache_key(func.__name__, *args, **kwargs)
            value = cache.get(key)
            if value is not None:
                return value
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result

        wrapper._cache = cache  # type: ignore
        wrapper.__wrapped__ = func  # type: ignore
        return wrapper

    return decorator


def create_cache(
    max_size: int = 1000,
    ttl: Optional[float] = None,
    policy: str = "lru",
) -> Cache:
    """Create a cache instance.

    Args:
        max_size: Maximum number of entries.
        ttl: Default time-to-live in seconds (None = no expiry).
        policy: Eviction policy ('lru', 'lfu', 'fifo', 'ttl').
    """
    policy_map = {
        "lru": EvictionPolicy.LRU,
        "lfu": EvictionPolicy.LFU,
        "fifo": EvictionPolicy.FIFO,
        "ttl": EvictionPolicy.TTL,
    }
    p = policy_map.get(policy, EvictionPolicy.LRU)
    return Cache(max_size=max_size, default_ttl=ttl, policy=p)


def create_tiered_cache(
    l1_size: int = 100,
    l2_size: int = 10000,
    l1_ttl: Optional[float] = None,
    l2_ttl: Optional[float] = None,
) -> TieredCache:
    """Create a two-tier cache."""
    return TieredCache([
        Cache(max_size=l1_size, default_ttl=l1_ttl, policy=EvictionPolicy.LRU),
        Cache(max_size=l2_size, default_ttl=l2_ttl, policy=EvictionPolicy.LRU),
    ])


def create_compute_cache(
    loader: Callable[[str], Any],
    max_size: int = 1000,
    ttl: Optional[float] = None,
) -> ComputeCache:
    """Create a compute cache with a loader function."""
    return ComputeCache(loader=loader, max_size=max_size, default_ttl=ttl)
