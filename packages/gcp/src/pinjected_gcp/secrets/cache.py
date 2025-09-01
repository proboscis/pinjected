"""Caching layer for GCP Secret Manager operations."""

import time
from typing import Optional, Protocol, Dict, Any, Tuple
from threading import Lock

from loguru import logger
from pinjected import design, injected, instance

# Import protocols from client module
from .client import AGcpSecretValueProtocol, GcpSecretValueProtocol


# Cache storage and lock (module-level for persistence)
_secret_cache: Dict[str, Tuple[str, float]] = {}
_cache_lock = Lock()


class AGcpSecretValueCachedProtocol(Protocol):
    """Async protocol for fetching cached secret values."""

    async def __call__(
        self,
        secret_id: str,
        project_id: Optional[str] = None,
        version: str = "latest",
        cache_ttl: int = 3600,
    ) -> str: ...


class GcpSecretValueCachedProtocol(Protocol):
    """Sync protocol for fetching cached secret values."""

    def __call__(
        self,
        secret_id: str,
        project_id: Optional[str] = None,
        version: str = "latest",
        cache_ttl: int = 3600,
    ) -> str: ...


@injected(protocol=AGcpSecretValueCachedProtocol)
async def a_gcp_secret_value_cached(
    a_gcp_secret_value: AGcpSecretValueProtocol,
    gcp_project_id: str,
    logger: logger,
    /,
    secret_id: str,
    project_id: Optional[str] = None,
    version: str = "latest",
    cache_ttl: int = 3600,
) -> str:
    """
    Fetch a secret value with caching (async).

    This function caches secret values in memory to reduce API calls.
    Cache entries expire after the specified TTL.

    Args:
        secret_id: The ID of the secret to access
        project_id: The GCP project ID (uses injected default if not specified)
        version: The version of the secret (defaults to "latest")
        cache_ttl: Cache time-to-live in seconds (default 1 hour)

    Returns:
        The secret value as a string
    """
    if project_id is None:
        project_id = gcp_project_id

    # Create cache key
    cache_key = f"{project_id}:{secret_id}:{version}"

    # Check cache with lock
    with _cache_lock:
        if cache_key in _secret_cache:
            cached_value, cached_time = _secret_cache[cache_key]
            age = time.time() - cached_time

            if age < cache_ttl:
                logger.debug(
                    f"Cache hit for secret {secret_id} (age: {age:.1f}s, ttl: {cache_ttl}s)"
                )
                return cached_value
            else:
                logger.debug(f"Cache expired for secret {secret_id} (age: {age:.1f}s)")
                del _secret_cache[cache_key]

    # Fetch from GCP
    logger.info(f"Fetching secret {secret_id} from GCP (cache miss)")
    secret_value = await a_gcp_secret_value(
        secret_id=secret_id, project_id=project_id, version=version
    )

    # Update cache with lock
    with _cache_lock:
        _secret_cache[cache_key] = (secret_value, time.time())
        logger.debug(f"Cached secret {secret_id} with TTL {cache_ttl}s")

    return secret_value


@injected(protocol=GcpSecretValueCachedProtocol)
def gcp_secret_value_cached(
    gcp_secret_value: GcpSecretValueProtocol,
    gcp_project_id: str,
    logger: logger,
    /,
    secret_id: str,
    project_id: Optional[str] = None,
    version: str = "latest",
    cache_ttl: int = 3600,
) -> str:
    """
    Fetch a secret value with caching (sync).

    This function caches secret values in memory to reduce API calls.
    Cache entries expire after the specified TTL.

    Args:
        secret_id: The ID of the secret to access
        project_id: The GCP project ID (uses injected default if not specified)
        version: The version of the secret (defaults to "latest")
        cache_ttl: Cache time-to-live in seconds (default 1 hour)

    Returns:
        The secret value as a string
    """
    if project_id is None:
        project_id = gcp_project_id

    # Create cache key
    cache_key = f"{project_id}:{secret_id}:{version}"

    # Check cache with lock
    with _cache_lock:
        if cache_key in _secret_cache:
            cached_value, cached_time = _secret_cache[cache_key]
            age = time.time() - cached_time

            if age < cache_ttl:
                logger.debug(
                    f"Cache hit for secret {secret_id} (age: {age:.1f}s, ttl: {cache_ttl}s)"
                )
                return cached_value
            else:
                logger.debug(f"Cache expired for secret {secret_id} (age: {age:.1f}s)")
                del _secret_cache[cache_key]

    # Fetch from GCP
    logger.info(f"Fetching secret {secret_id} from GCP (cache miss)")
    secret_value = gcp_secret_value(
        secret_id=secret_id, project_id=project_id, version=version
    )

    # Update cache with lock
    with _cache_lock:
        _secret_cache[cache_key] = (secret_value, time.time())
        logger.debug(f"Cached secret {secret_id} with TTL {cache_ttl}s")

    return secret_value


@instance
def clear_secret_cache_command() -> int:
    """
    Clear all cached secrets (injectable version).

    Returns:
        Number of cache entries cleared
    """
    with _cache_lock:
        count = len(_secret_cache)
        _secret_cache.clear()
        logger.info(f"Cleared {count} cached secrets")
        return count


@instance
def get_cache_stats_command() -> Dict[str, Any]:
    """
    Get statistics about the secret cache (injectable version).

    Returns:
        Dictionary with cache statistics
    """
    with _cache_lock:
        current_time = time.time()
        stats = {"total_entries": len(_secret_cache), "entries": []}

        for key, (_, cached_time) in _secret_cache.items():
            project, secret_id, version = key.split(":", 2)
            age = current_time - cached_time
            stats["entries"].append(
                {
                    "project": project,
                    "secret_id": secret_id,
                    "version": version,
                    "age_seconds": age,
                }
            )

        return stats


# Design for cache module
__design__ = design(
    # Cached operations
    a_gcp_secret_value_cached=a_gcp_secret_value_cached,
    gcp_secret_value_cached=gcp_secret_value_cached,
    # Cache management commands (as @instance for injection)
    clear_secret_cache_command=clear_secret_cache_command,
    get_cache_stats_command=get_cache_stats_command,
)
