"""Disk cache for search results and page content.

Avoids redundant network requests across research iterations and sessions.
Cache is stored in ~/.cache/deepworm/ with configurable TTL.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "deepworm"
DEFAULT_TTL = 3600 * 24  # 24 hours


class Cache:
    """Simple disk-based cache with TTL support."""

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        ttl: int = DEFAULT_TTL,
        enabled: bool = True,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.ttl = ttl
        self.enabled = enabled
        self._hits = 0
        self._misses = 0

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(namespace: str, value: str) -> str:
        """Generate a cache key from namespace and value."""
        raw = f"{namespace}:{value}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Use first 2 chars as subdirectory to avoid too many files in one dir
        subdir = self.cache_dir / key[:2]
        subdir.mkdir(exist_ok=True)
        return subdir / f"{key}.json"

    def get(self, namespace: str, value: str) -> Optional[Any]:
        """Get a value from cache. Returns None if not found or expired."""
        if not self.enabled:
            return None

        key = self._key(namespace, value)
        path = self._path(key)

        if not path.exists():
            self._misses += 1
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._misses += 1
            return None

        # Check TTL
        if time.time() - data.get("ts", 0) > self.ttl:
            logger.debug("Cache expired: %s:%s", namespace, value[:60])
            path.unlink(missing_ok=True)
            self._misses += 1
            return None

        self._hits += 1
        logger.debug("Cache hit: %s:%s", namespace, value[:60])
        return data.get("value")

    def set(self, namespace: str, value: str, data: Any) -> None:
        """Store a value in cache."""
        if not self.enabled:
            return

        key = self._key(namespace, value)
        path = self._path(key)

        entry = {"ts": time.time(), "ns": namespace, "value": data}

        try:
            path.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
            logger.debug("Cache set: %s:%s", namespace, value[:60])
        except OSError as e:
            logger.warning("Cache write failed: %s", e)

    def clear(self) -> int:
        """Clear all cache entries. Returns number of entries removed."""
        if not self.cache_dir.exists():
            return 0

        count = 0
        for path in self.cache_dir.rglob("*.json"):
            try:
                path.unlink()
                count += 1
            except OSError:
                pass

        # Clean up empty subdirectories
        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                try:
                    subdir.rmdir()  # Only removes if empty
                except OSError:
                    pass

        logger.info("Cache cleared: %d entries removed", count)
        return count

    def stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0.0,
        }

    @property
    def size(self) -> int:
        """Return number of cached entries."""
        if not self.cache_dir.exists():
            return 0
        return sum(1 for _ in self.cache_dir.rglob("*.json"))


# Module-level default cache instance
_default_cache: Optional[Cache] = None


def get_cache(enabled: bool = True) -> Cache:
    """Get or create the default cache instance."""
    global _default_cache
    if _default_cache is None:
        _default_cache = Cache(enabled=enabled)
    return _default_cache
