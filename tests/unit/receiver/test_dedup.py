"""Unit tests for the InMemoryDedup deduplication store."""

import time
from unittest.mock import patch

from box2.receiver.dedup import InMemoryDedup

# ============================================================================
# Core Deduplication Tests
# ============================================================================


def test_first_occurrence_is_not_duplicate():
    """A key that has never been seen should not be a duplicate."""
    store = InMemoryDedup(window_seconds=300)

    assert store.is_duplicate("key-1") is False


def test_same_key_within_window_is_duplicate():
    """A key seen again within the dedup window should be a duplicate."""
    store = InMemoryDedup(window_seconds=300)

    store.record("key-1")

    assert store.is_duplicate("key-1") is True


def test_same_key_outside_window_is_not_duplicate():
    """A key seen again after the dedup window has elapsed should not be a duplicate."""
    store = InMemoryDedup(window_seconds=1)

    store.record("key-1")

    # Simulate time passing beyond the window
    with patch("box2.receiver.dedup.time.monotonic", return_value=time.monotonic() + 2):
        assert store.is_duplicate("key-1") is False


def test_different_keys_are_independent():
    """Different keys should be tracked independently."""
    store = InMemoryDedup(window_seconds=300)

    store.record("key-1")

    assert store.is_duplicate("key-1") is True
    assert store.is_duplicate("key-2") is False


def test_cleanup_removes_expired_entries():
    """Expired entries should be removed during cleanup."""
    store = InMemoryDedup(window_seconds=1)

    store.record("key-1")
    store.record("key-2")

    # Simulate time passing beyond the window
    future_time = time.monotonic() + 2
    with patch("box2.receiver.dedup.time.monotonic", return_value=future_time):
        # is_duplicate triggers cleanup
        store.is_duplicate("key-new")

    assert len(store._seen) == 0


def test_record_updates_timestamp():
    """Recording an existing key should update its timestamp."""
    store = InMemoryDedup(window_seconds=300)

    store.record("key-1")
    first_ts = store._seen["key-1"]

    # Small delay to ensure monotonic clock advances
    store.record("key-1")
    second_ts = store._seen["key-1"]

    assert second_ts >= first_ts
