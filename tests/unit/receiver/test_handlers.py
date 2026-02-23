"""Unit tests for notification handler logic."""

from unittest.mock import patch

from box2.receiver.config import ReceiverConfig
from box2.receiver.dedup import InMemoryDedup
from box2.receiver.handlers import build_dedup_key, process_notifications
from box2.receiver.models import Notification, NotificationPayload

# ============================================================================
# Fixtures
# ============================================================================

CONFIG = ReceiverConfig(client_state="test-secret")

VALID_NOTIFICATION = {
    "subscriptionId": "sub-abc-123",
    "changeType": "created",
    "clientState": "test-secret",
    "resource": "sites/site-id/lists/list-id/items/42",
    "tenantId": "tenant-id-999",
}


def _payload(*notifications: dict) -> NotificationPayload:
    """Build a NotificationPayload from raw notification dicts."""
    return NotificationPayload.model_validate({"value": list(notifications)})


# ============================================================================
# build_dedup_key Tests
# ============================================================================


def test_dedup_key_includes_subscription_resource_and_change_type():
    """Dedup key should combine subscriptionId, resource, and changeType."""
    notification = Notification.model_validate(VALID_NOTIFICATION)
    key = build_dedup_key(notification)

    assert "sub-abc-123" in key
    assert "sites/site-id/lists/list-id/items/42" in key
    assert "created" in key


def test_dedup_key_differs_for_different_change_types():
    """Different change types on the same resource should produce different keys."""
    created = Notification.model_validate(VALID_NOTIFICATION)
    updated = Notification.model_validate({**VALID_NOTIFICATION, "changeType": "updated"})

    assert build_dedup_key(created) != build_dedup_key(updated)


# ============================================================================
# process_notifications Tests
# ============================================================================


@patch("box2.receiver.handlers.dispatch")
def test_process_valid_notification_dispatches(mock_dispatch):
    """A valid notification should be dispatched."""
    store = InMemoryDedup()
    payload = _payload(VALID_NOTIFICATION)

    dispatched = process_notifications(payload, CONFIG, store)

    assert dispatched == 1
    mock_dispatch.assert_called_once()


@patch("box2.receiver.handlers.dispatch")
def test_process_skips_wrong_client_state(mock_dispatch):
    """A notification with wrong clientState should be skipped."""
    store = InMemoryDedup()
    bad_notification = {**VALID_NOTIFICATION, "clientState": "wrong-secret"}
    payload = _payload(bad_notification)

    dispatched = process_notifications(payload, CONFIG, store)

    assert dispatched == 0
    mock_dispatch.assert_not_called()


@patch("box2.receiver.handlers.dispatch")
def test_process_skips_duplicate_notification(mock_dispatch):
    """A duplicate notification should be skipped on the second call."""
    store = InMemoryDedup()
    payload = _payload(VALID_NOTIFICATION)

    # First call — dispatched
    dispatched_1 = process_notifications(payload, CONFIG, store)
    # Second call — duplicate
    dispatched_2 = process_notifications(payload, CONFIG, store)

    assert dispatched_1 == 1
    assert dispatched_2 == 0
    mock_dispatch.assert_called_once()


@patch("box2.receiver.handlers.dispatch")
def test_process_multiple_notifications(mock_dispatch):
    """Multiple valid notifications should each be dispatched."""
    store = InMemoryDedup()
    second = {**VALID_NOTIFICATION, "subscriptionId": "sub-def-456"}
    payload = _payload(VALID_NOTIFICATION, second)

    dispatched = process_notifications(payload, CONFIG, store)

    assert dispatched == 2
    assert mock_dispatch.call_count == 2


@patch("box2.receiver.handlers.dispatch")
def test_process_empty_payload(mock_dispatch):
    """An empty notification payload should dispatch nothing."""
    store = InMemoryDedup()
    payload = _payload()

    dispatched = process_notifications(payload, CONFIG, store)

    assert dispatched == 0
    mock_dispatch.assert_not_called()


@patch("box2.receiver.handlers.dispatch")
def test_process_mixed_valid_and_invalid(mock_dispatch):
    """Only valid notifications should be dispatched; invalid ones should be skipped."""
    store = InMemoryDedup()
    bad = {**VALID_NOTIFICATION, "clientState": "wrong", "subscriptionId": "sub-bad"}
    payload = _payload(VALID_NOTIFICATION, bad)

    dispatched = process_notifications(payload, CONFIG, store)

    assert dispatched == 1
    mock_dispatch.assert_called_once()
