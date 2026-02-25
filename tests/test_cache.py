"""Tests for deepworm.cache."""

import json
import time

from deepworm.cache import Cache


def test_get_set(tmp_path):
    """Cache should store and retrieve values."""
    cache = Cache(cache_dir=tmp_path, ttl=60)
    cache.set("test", "key1", {"data": "hello"})
    result = cache.get("test", "key1")
    assert result == {"data": "hello"}


def test_miss(tmp_path):
    """Cache should return None for missing keys."""
    cache = Cache(cache_dir=tmp_path, ttl=60)
    assert cache.get("test", "nonexistent") is None


def test_expired(tmp_path):
    """Cache should return None for expired entries."""
    cache = Cache(cache_dir=tmp_path, ttl=1)
    cache.set("test", "key1", "value")
    # Manually backdate the timestamp
    key = cache._key("test", "key1")
    path = cache._path(key)
    data = json.loads(path.read_text())
    data["ts"] = time.time() - 10  # 10 seconds ago
    path.write_text(json.dumps(data))
    assert cache.get("test", "key1") is None


def test_disabled(tmp_path):
    """Disabled cache should always return None."""
    cache = Cache(cache_dir=tmp_path, enabled=False)
    cache.set("test", "key1", "value")
    assert cache.get("test", "key1") is None


def test_clear(tmp_path):
    """Clear should remove all entries."""
    cache = Cache(cache_dir=tmp_path, ttl=60)
    cache.set("test", "k1", "v1")
    cache.set("test", "k2", "v2")
    cache.set("test", "k3", "v3")
    count = cache.clear()
    assert count == 3
    assert cache.get("test", "k1") is None


def test_stats(tmp_path):
    """Stats should track hits and misses."""
    cache = Cache(cache_dir=tmp_path, ttl=60)
    cache.set("test", "key1", "value")
    cache.get("test", "key1")  # hit
    cache.get("test", "key2")  # miss
    cache.get("test", "key1")  # hit
    stats = cache.stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 66.7


def test_size(tmp_path):
    """Size should return number of entries."""
    cache = Cache(cache_dir=tmp_path, ttl=60)
    assert cache.size == 0
    cache.set("test", "k1", "v1")
    cache.set("test", "k2", "v2")
    assert cache.size == 2


def test_string_value(tmp_path):
    """Cache should handle plain string values."""
    cache = Cache(cache_dir=tmp_path, ttl=60)
    cache.set("page", "https://example.com", "Hello world page content")
    result = cache.get("page", "https://example.com")
    assert result == "Hello world page content"


def test_list_value(tmp_path):
    """Cache should handle list values (search results)."""
    cache = Cache(cache_dir=tmp_path, ttl=60)
    results = [
        {"title": "Result 1", "url": "https://a.com", "snippet": "text 1"},
        {"title": "Result 2", "url": "https://b.com", "snippet": "text 2"},
    ]
    cache.set("search", "python web scraping", results)
    cached = cache.get("search", "python web scraping")
    assert len(cached) == 2
    assert cached[0]["title"] == "Result 1"
