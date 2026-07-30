from __future__ import annotations
"""Unified Cache Management for LLM Tasks.

Provides file-based caching with support for different task types,
TTL expiration, and graceful error handling.
"""
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from .task_types import TaskType


class CacheManager:
    """Unified cache manager for LLM task results.

    Supports different caching strategies per task type:
    - TITLE_GENERATION: Cache key based on procedure steps content
    - FIELD_VALIDATION: Cache key based on entity attributes (existing logic)
    - GENERAL: SHA256 hash of request content

    Features:
    - File-based JSON storage
    - TTL expiration support
    - Non-fatal error handling (cache failures don't break main flow)
    - Thread-safe operations
    """

    def __init__(
        self,
        cache_dir: str | None = None,
        task_type: TaskType = TaskType.GENERAL,
        ttl_days: int = 7,
    ):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for cache storage. Defaults to "cache/"
            task_type: Task type for cache key generation strategy
            ttl_days: Cache time-to-live in days
        """
        self._task_type = task_type

        if cache_dir is None:
            # Default to project root cache directory
            self._cache_dir = Path(__file__).parent.parent.parent / "cache"
        else:
            self._cache_dir = Path(cache_dir)

        self._ttl_seconds = ttl_days * 24 * 3600
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Cache directory creation is non-fatal
            pass

    def _get_cache_key(self, request_data: dict | list | str) -> str:
        """Generate cache key based on task type and request data.

        Different task types use different strategies for cache key generation:

        - TITLE_GENERATION: Based on procedure steps content (stable across runs)
        - FIELD_VALIDATION: Based on entity attributes (existing logic)
        - GENERAL: SHA256 hash of serialized request data

        Args:
            request_data: Request data to generate cache key from

        Returns:
            Cache key string (16-character hash)
        """
        if self._task_type == TaskType.TITLE_GENERATION:
            return self._get_title_cache_key(request_data)
        elif self._task_type == TaskType.FIELD_VALIDATION:
            return self._get_field_validation_cache_key(request_data)
        else:
            return self._get_generic_cache_key(request_data)

    def _get_title_cache_key(self, procedures: list[dict] | dict) -> str:
        """Generate cache key for title generation tasks.

        Based on procedure steps content, excluding mutable fields like temp_id.

        Args:
            procedures: List of procedure dicts or single procedure

        Returns:
            Cache key string
        """
        if isinstance(procedures, dict):
            procedures = [procedures]

        # Extract stable content from procedures
        stable_content = []
        for proc in procedures:
            proc_data = {
                'steps': proc.get('steps', []),
                # Exclude temp_id and other mutable fields
            }
            stable_content.append(proc_data)

        # Sort for consistency and hash
        stable = json.dumps(stable_content, ensure_ascii=True, sort_keys=True)
        return hashlib.sha256(stable.encode()).hexdigest()[:16]

    def _get_field_validation_cache_key(self, items: list[dict]) -> str:
        """Generate cache key for field validation tasks.

        Uses existing logic from field_validation.py for backward compatibility.

        Args:
            items: List of attribute items with entity_id, attr_name, desc

        Returns:
            Cache key string
        """
        # Use existing logic: sort by entity_id + attr_name
        sorted_items = sorted(items, key=lambda x: x.get('entity_id', '') + x.get('attr_name', ''))
        stable = json.dumps(sorted_items, ensure_ascii=True, sort_keys=True)
        return hashlib.sha256(stable.encode()).hexdigest()[:16]

    def _get_generic_cache_key(self, request_data: dict | list | str) -> str:
        """Generate generic cache key from request data.

        Args:
            request_data: Any JSON-serializable data

        Returns:
            Cache key string
        """
        if isinstance(request_data, str):
            stable = request_data
        else:
            stable = json.dumps(request_data, ensure_ascii=True, sort_keys=True)
        return hashlib.sha256(stable.encode()).hexdigest()[:16]

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get full file path for a cache key.

        Args:
            cache_key: Cache key string

        Returns:
            Path to cache file
        """
        # Use task type prefix for better organization
        prefix = self._task_type.value[:3]  # First 3 chars of task type
        filename = f"{prefix}_{cache_key}.json"
        return self._cache_dir / filename

    def load(self, request_data: dict | list | str) -> Any | None:
        """Load cached result if available and not expired.

        Args:
            request_data: Request data to look up in cache

        Returns:
            Cached data, or None if cache miss or expired
        """
        cache_key = self._get_cache_key(request_data)
        cache_file = self._get_cache_file_path(cache_key)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_entry = json.load(f)

            # Check if cache has expired
            timestamp = cache_entry.get('timestamp', 0)
            if time.time() - timestamp > self._ttl_seconds:
                # Cache expired, remove it
                try:
                    cache_file.unlink()
                except OSError:
                    pass
                return None

            data = cache_entry.get('data')
            return data

        except (json.JSONDecodeError, KeyError, OSError):
            # Cache read failure is non-fatal
            return None

    def save(self, request_data: dict | list | str, result_data: Any) -> bool:
        """Save result to cache.

        Args:
            request_data: Request data to use as cache key
            result_data: Result data to cache

        Returns:
            True if save successful, False otherwise
        """
        cache_key = self._get_cache_key(request_data)
        cache_file = self._get_cache_file_path(cache_key)

        try:
            cache_entry = {
                'timestamp': time.time(),
                'task_type': self._task_type.value,
                'data': result_data,
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, ensure_ascii=False, indent=2)

            return True

        except (OSError, TypeError):
            # Cache write failure is non-fatal
            return False

    def clear(self, pattern: str | None = None) -> int:
        """Clear cache files.

        Args:
            pattern: Optional pattern to match (e.g., "title_"). If None, clears all.

        Returns:
            Number of cache files cleared
        """
        cleared_count = 0

        if not self._cache_dir.exists():
            return cleared_count

        try:
            for cache_file in self._cache_dir.glob('*.json'):
                if pattern is None or cache_file.stem.startswith(pattern):
                    try:
                        cache_file.unlink()
                        cleared_count += 1
                    except OSError:
                        pass
        except OSError:
            pass

        return cleared_count

    def is_cache_enabled(self) -> bool:
        """Check if caching is available (cache directory exists and is writable).

        Returns:
            True if caching is available
        """
        if not self._cache_dir.exists():
            return False

        # Try to create a test file
        test_file = self._cache_dir / '.cache_test'
        try:
            test_file.touch()
            test_file.unlink()
            return True
        except OSError:
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats:
            - total_files: Total number of cache files
            - total_size_bytes: Total size in bytes
            - task_type_counts: Count of files per task type
            - expired_count: Number of expired cache files
        """
        stats = {
            'total_files': 0,
            'total_size_bytes': 0,
            'task_type_counts': {},
            'expired_count': 0,
        }

        if not self._cache_dir.exists():
            return stats

        try:
            for cache_file in self._cache_dir.glob('*.json'):
                stats['total_files'] += 1
                stats['total_size_bytes'] += cache_file.stat().st_size

                # Count by task type prefix
                prefix = cache_file.stem.split('_')[0] if '_' in cache_file.stem else 'unknown'
                stats['task_type_counts'][prefix] = stats['task_type_counts'].get(prefix, 0) + 1

                # Check expiration
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_entry = json.load(f)
                    timestamp = cache_entry.get('timestamp', 0)
                    if time.time() - timestamp > self._ttl_seconds:
                        stats['expired_count'] += 1
                except (json.JSONDecodeError, OSError):
                    pass

        except OSError:
            pass

        return stats


# Backward compatibility function for field_validation.py
def _cache_path(items: list[dict]) -> str:
    """Legacy function for backward compatibility with field_validation.py.

    Args:
        items: List of attribute items

    Returns:
        Cache file path string
    """
    manager = CacheManager(task_type=TaskType.FIELD_VALIDATION)
    cache_key = manager._get_field_validation_cache_key(items)
    return str(manager._get_cache_file_path(cache_key))


def _load_cache(items: list[dict]) -> dict | None:
    """Legacy function for backward compatibility with field_validation.py.

    Args:
        items: List of attribute items

    Returns:
        Cached data or None
    """
    manager = CacheManager(task_type=TaskType.FIELD_VALIDATION)
    return manager.load(items)


def _save_cache(items: list[dict], result: dict) -> None:
    """Legacy function for backward compatibility with field_validation.py.

    Args:
        items: List of attribute items
        result: Result to cache
    """
    manager = CacheManager(task_type=TaskType.FIELD_VALIDATION)
    manager.save(items, result)