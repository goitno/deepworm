"""Tests for the caching module."""

import time

import pytest

from deepworm.caching import (
    Cache,
    CacheEntry,
    CacheStats,
    ComputeCache,
    EvictionPolicy,
    TieredCache,
    cache_key,
    create_cache,
    create_compute_cache,
    create_tiered_cache,
    memoize,
)


# ---------------------------------------------------------------------------
# EvictionPolicy
# ---------------------------------------------------------------------------


class TestEvictionPolicy:
    def test_all_policies(self):
        assert len(EvictionPolicy) == 4


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------


class TestCacheEntry:
    def test_not_expired_without_ttl(self):
        entry = CacheEntry(key="k", value="v")
        assert not entry.is_expired

    def test_expired_with_ttl(self):
        entry = CacheEntry(key="k", value="v", created_at=time.time() - 10, ttl=5)
        assert entry.is_expired

    def test_not_expired_within_ttl(self):
        entry = CacheEntry(key="k", value="v", ttl=3600)
        assert not entry.is_expired

    def test_age(self):
        entry = CacheEntry(key="k", value="v", created_at=time.time() - 5)
        assert entry.age >= 4.9

    def test_to_dict(self):
        entry = CacheEntry(key="test", value="val", access_count=3)
        d = entry.to_dict()
        assert d["key"] == "test"
        assert d["access_count"] == 3
        assert "is_expired" in d


# ---------------------------------------------------------------------------
# CacheStats
# ---------------------------------------------------------------------------


class TestCacheStats:
    def test_initial_stats(self):
        s = CacheStats()
        assert s.hits == 0
        assert s.misses == 0
        assert s.total_requests == 0
        assert s.hit_rate == 0.0

    def test_hit_rate(self):
        s = CacheStats(hits=3, misses=1)
        assert s.hit_rate == 0.75
        assert s.miss_rate == 0.25

    def test_reset(self):
        s = CacheStats(hits=10, misses=5)
        s.reset()
        assert s.hits == 0
        assert s.total_requests == 0

    def test_to_dict(self):
        s = CacheStats(hits=2, misses=3)
        d = s.to_dict()
        assert d["hits"] == 2
        assert d["total_requests"] == 5


# ---------------------------------------------------------------------------
# Cache — basic operations
# ---------------------------------------------------------------------------


class TestCacheBasic:
    def test_get_set(self):
        cache = Cache(max_size=10)
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_get_missing(self):
        cache = Cache()
        assert cache.get("missing") is None
        assert cache.get("missing", "default") == "default"

    def test_delete(self):
        cache = Cache()
        cache.set("key", "value")
        assert cache.delete("key") is True
        assert cache.get("key") is None
        assert cache.delete("key") is False

    def test_has(self):
        cache = Cache()
        cache.set("k", "v")
        assert cache.has("k")
        assert not cache.has("missing")

    def test_clear(self):
        cache = Cache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.clear() == 2
        assert cache.size == 0

    def test_keys_values_items(self):
        cache = Cache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert set(cache.keys()) == {"a", "b"}
        assert set(cache.values()) == {1, 2}
        assert len(cache.items()) == 2

    def test_size(self):
        cache = Cache(max_size=5)
        assert cache.size == 0
        cache.set("a", 1)
        assert cache.size == 1

    def test_get_entry(self):
        cache = Cache()
        cache.set("k", "v")
        entry = cache.get_entry("k")
        assert entry is not None
        assert entry.key == "k"
        assert entry.value == "v"

    def test_overwrite(self):
        cache = Cache()
        cache.set("k", 1)
        cache.set("k", 2)
        assert cache.get("k") == 2

    def test_stats_tracking(self):
        cache = Cache()
        cache.set("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        assert cache.stats.hits == 1
        assert cache.stats.misses == 1
        assert cache.stats.sets == 1

    def test_to_dict(self):
        cache = Cache(max_size=100)
        d = cache.to_dict()
        assert d["max_size"] == 100
        assert "stats" in d


# ---------------------------------------------------------------------------
# Cache — eviction
# ---------------------------------------------------------------------------


class TestCacheEviction:
    def test_lru_eviction(self):
        cache = Cache(max_size=3, policy=EvictionPolicy.LRU)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")  # access 'a' to make it recent
        cache.set("d", 4)  # should evict 'b' (least recently used)
        assert cache.get("a") == 1
        assert cache.get("b") is None  # evicted
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_lfu_eviction(self):
        cache = Cache(max_size=3, policy=EvictionPolicy.LFU)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")  # access count: 1
        cache.get("a")  # access count: 2
        cache.get("b")  # access count: 1
        cache.set("d", 4)  # should evict 'c' (least frequently used, 0 accesses)
        assert cache.get("a") is not None
        assert cache.get("c") is None  # evicted

    def test_fifo_eviction(self):
        cache = Cache(max_size=2, policy=EvictionPolicy.FIFO)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # should evict 'a'
        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_eviction_stats(self):
        cache = Cache(max_size=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # evicts
        assert cache.stats.evictions == 1


# ---------------------------------------------------------------------------
# Cache — TTL
# ---------------------------------------------------------------------------


class TestCacheTTL:
    def test_ttl_expiry(self):
        cache = Cache()
        cache.set("k", "v", ttl=0.01)
        assert cache.get("k") == "v"
        time.sleep(0.02)
        assert cache.get("k") is None

    def test_default_ttl(self):
        cache = Cache(default_ttl=0.01)
        cache.set("k", "v")
        time.sleep(0.02)
        assert cache.get("k") is None

    def test_per_key_ttl_override(self):
        cache = Cache(default_ttl=3600)
        cache.set("short", "v", ttl=0.01)
        cache.set("long", "v")
        time.sleep(0.02)
        assert cache.get("short") is None
        assert cache.get("long") == "v"

    def test_has_expired(self):
        cache = Cache()
        cache.set("k", "v", ttl=0.01)
        time.sleep(0.02)
        assert not cache.has("k")


# ---------------------------------------------------------------------------
# TieredCache
# ---------------------------------------------------------------------------


class TestTieredCache:
    def test_get_set(self):
        tc = TieredCache([Cache(max_size=5), Cache(max_size=50)])
        tc.set("k", "v")
        assert tc.get("k") == "v"

    def test_promotion(self):
        l1 = Cache(max_size=5)
        l2 = Cache(max_size=50)
        tc = TieredCache([l1, l2])
        # Set only in L2
        l2.set("k", "v")
        assert l1.get("k") is None
        # Get through tiered cache promotes to L1
        assert tc.get("k") == "v"
        assert l1.get("k") == "v"  # now in L1

    def test_delete_all_tiers(self):
        tc = TieredCache([Cache(max_size=5), Cache(max_size=50)])
        tc.set("k", "v")
        assert tc.delete("k")
        assert tc.get("k") is None

    def test_clear(self):
        tc = TieredCache([Cache(max_size=5), Cache(max_size=50)])
        tc.set("a", 1)
        tc.set("b", 2)
        total = tc.clear()
        assert total == 4  # 2 in each tier

    def test_stats(self):
        tc = create_tiered_cache()
        s = tc.stats()
        assert len(s) == 2

    def test_tier_count(self):
        tc = TieredCache()
        assert tc.tier_count == 2


# ---------------------------------------------------------------------------
# ComputeCache
# ---------------------------------------------------------------------------


class TestComputeCache:
    def test_compute_on_miss(self):
        computed = []
        def loader(key):
            computed.append(key)
            return f"value_{key}"

        cc = ComputeCache(loader=loader, max_size=10)
        assert cc.get("a") == "value_a"
        assert cc.get("a") == "value_a"
        assert len(computed) == 1  # only computed once

    def test_invalidate(self):
        cc = ComputeCache(loader=lambda k: k.upper(), max_size=10)
        cc.get("hello")
        assert cc.invalidate("hello")
        assert cc.size == 0

    def test_clear(self):
        cc = ComputeCache(loader=lambda k: k, max_size=10)
        cc.get("a")
        cc.get("b")
        assert cc.clear() == 2

    def test_stats(self):
        cc = ComputeCache(loader=lambda k: k, max_size=10)
        cc.get("a")
        cc.get("a")  # hit
        assert cc.stats.hits >= 1


# ---------------------------------------------------------------------------
# cache_key
# ---------------------------------------------------------------------------


class TestCacheKey:
    def test_deterministic(self):
        k1 = cache_key("func", "arg1", x=1)
        k2 = cache_key("func", "arg1", x=1)
        assert k1 == k2

    def test_different_inputs(self):
        k1 = cache_key("a", 1)
        k2 = cache_key("b", 2)
        assert k1 != k2

    def test_kwargs_order_independent(self):
        k1 = cache_key(a=1, b=2)
        k2 = cache_key(b=2, a=1)
        assert k1 == k2


# ---------------------------------------------------------------------------
# memoize
# ---------------------------------------------------------------------------


class TestMemoize:
    def test_memoize_basic(self):
        call_count = [0]

        @memoize(max_size=10)
        def add(a, b):
            call_count[0] += 1
            return a + b

        assert add(1, 2) == 3
        assert add(1, 2) == 3
        assert call_count[0] == 1  # only called once

    def test_memoize_different_args(self):
        @memoize()
        def square(n):
            return n * n

        assert square(3) == 9
        assert square(4) == 16

    def test_memoize_has_cache(self):
        @memoize()
        def f(x):
            return x

        assert hasattr(f, "_cache")


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


class TestFactoryFunctions:
    def test_create_cache(self):
        c = create_cache(max_size=50, policy="lfu")
        assert c.max_size == 50
        assert c.policy == EvictionPolicy.LFU

    def test_create_cache_default(self):
        c = create_cache()
        assert c.policy == EvictionPolicy.LRU

    def test_create_tiered_cache(self):
        tc = create_tiered_cache(l1_size=10, l2_size=100)
        assert tc.tier_count == 2

    def test_create_compute_cache(self):
        cc = create_compute_cache(loader=lambda k: k * 2, max_size=50)
        assert cc.get("abc") == "abcabc"
