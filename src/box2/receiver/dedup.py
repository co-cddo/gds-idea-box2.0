"""Pluggable deduplication for webhook notifications.

Microsoft Graph may send multiple notifications for the same change event.
A deduplication store tracks recently processed notification keys and
suppresses duplicates within a configurable time window.

The ``DeduplicationStore`` protocol allows swapping backends (in-memory for
local dev, DynamoDB for Lambda deployments) without changing handler code.
"""

import logging
import time
from typing import Protocol

logger = logging.getLogger(__name__)


class DeduplicationStore(Protocol):
    """Interface for notification deduplication backends."""

    def is_duplicate(self, key: str) -> bool:
        """Check if a notification key has been seen within the dedup window.

        Args:
            key: A unique identifier for the notification event.

        Returns:
            True if the key was already recorded within the window.
        """
        ...

    def record(self, key: str) -> None:
        """Record a notification key as processed.

        Args:
            key: A unique identifier for the notification event.
        """
        ...


class InMemoryDedup:
    """In-memory deduplication store using a dict with TTL-based expiry.

    Suitable for single-instance deployments and local development.
    For Lambda or multi-instance deployments, use a shared store
    (e.g. DynamoDB) that implements the ``DeduplicationStore`` protocol.

    Args:
        window_seconds: Time window during which a key is considered a duplicate.
    """

    def __init__(self, window_seconds: int = 300):
        self._window_seconds = window_seconds
        self._seen: dict[str, float] = {}

    def is_duplicate(self, key: str) -> bool:
        """Check if a notification key was recorded within the dedup window.

        Also performs lazy cleanup of expired entries.

        Args:
            key: A unique identifier for the notification event.

        Returns:
            True if the key exists and has not expired.
        """
        self._cleanup()
        now = time.monotonic()

        if key in self._seen:
            elapsed = now - self._seen[key]
            if elapsed < self._window_seconds:
                logger.debug("Duplicate key detected: %s (%.0fs ago)", key, elapsed)
                return True

        return False

    def record(self, key: str) -> None:
        """Record a notification key with the current timestamp.

        Args:
            key: A unique identifier for the notification event.
        """
        self._seen[key] = time.monotonic()
        logger.debug("Recorded key: %s", key)

    def _cleanup(self) -> None:
        """Remove entries older than the dedup window."""
        now = time.monotonic()
        expired = [k for k, ts in self._seen.items() if now - ts >= self._window_seconds]
        for k in expired:
            del self._seen[k]
        if expired:
            logger.debug("Cleaned up %d expired dedup entries", len(expired))
