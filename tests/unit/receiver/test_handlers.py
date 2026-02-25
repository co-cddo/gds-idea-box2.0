"""Unit tests for notification handler logic."""

from unittest.mock import MagicMock

import pytest

from box2.receiver.config import ReceiverConfig
from box2.receiver.dedup import InMemoryDedup
from box2.receiver.handlers import (
    _is_self_write,
    dispatch_route,
)
from box2.receiver.models import NotificationPayload
from box2.receiver.routes import WebhookRoute

# ============================================================================
# Fixtures
# ============================================================================

APP_IDENTITY = "test-app-id"
CONFIG = ReceiverConfig(client_state="test-secret", app_identity=APP_IDENTITY)

VALID_NOTIFICATION = {
    "subscriptionId": "sub-abc-123",
    "changeType": "updated",
    "clientState": "test-secret",
    "resource": "sites/site-id/lists/list-id/items/1",
    "tenantId": "tenant-id-999",
    "resourceData": {
        "@odata.type": "#Microsoft.Graph.listItem",
        "@odata.id": "sites/site-id/lists/list-id/items/1",
        "id": "1",
    },
}

WRONG_STATE_NOTIFICATION = {
    **VALID_NOTIFICATION,
    "clientState": "wrong-secret",
}


def _make_item(
    item_id: str = "1",
    last_modified: str = "2026-02-23T12:00:00Z",
    modified_by_app: str | None = None,
) -> dict:
    """Build a canned list item response."""
    item = {
        "id": item_id,
        "lastModifiedDateTime": last_modified,
        "fields": {"Title": f"Item {item_id}"},
    }
    if modified_by_app:
        item["lastModifiedBy"] = {"application": {"id": modified_by_app}}
    else:
        item["lastModifiedBy"] = {"user": {"id": "human-user-123"}}
    return item


def _make_notification(item_id: str = "1", **overrides) -> dict:
    """Build a notification dict with resourceData pointing at an item."""
    base = {
        **VALID_NOTIFICATION,
        "resource": f"sites/site-id/lists/list-id/items/{item_id}",
        "resourceData": {
            "@odata.type": "#Microsoft.Graph.listItem",
            "@odata.id": f"sites/site-id/lists/list-id/items/{item_id}",
            "id": item_id,
        },
    }
    base.update(overrides)
    return base


def _make_mock_resource(items: dict[str, dict] | None = None) -> MagicMock:
    """Build a mock resource with a get_item method.

    Args:
        items: Mapping of item_id -> item dict. get_item returns the
            matching item or raises KeyError.
    """
    resource = MagicMock()
    if items:
        resource.get_item.side_effect = lambda item_id: items[item_id]
    else:
        resource.get_item.return_value = _make_item()
    return resource


# ============================================================================
# _is_self_write Tests
# ============================================================================


def test_is_self_write_returns_true_for_app_modified():
    """Items modified by the app's service principal should be detected."""
    item = _make_item(modified_by_app=APP_IDENTITY)

    assert _is_self_write(item, APP_IDENTITY) is True


def test_is_self_write_returns_false_for_human_modified():
    """Items modified by a human user should not be detected as self-writes."""
    item = _make_item()

    assert _is_self_write(item, APP_IDENTITY) is False


def test_is_self_write_returns_false_for_different_app():
    """Items modified by a different app should not be detected as self-writes."""
    item = _make_item(modified_by_app="other-app-id")

    assert _is_self_write(item, APP_IDENTITY) is False


def test_is_self_write_handles_missing_lastmodifiedby():
    """Items without lastModifiedBy should return False (not crash)."""
    item = {"id": "1", "lastModifiedDateTime": "2026-02-23T12:00:00Z", "fields": {}}

    assert _is_self_write(item, APP_IDENTITY) is False


# ============================================================================
# dispatch_route Tests
# ============================================================================


def _make_payload(*notifications: dict) -> NotificationPayload:
    """Build a NotificationPayload from notification dicts."""
    return NotificationPayload.model_validate({"value": list(notifications)})


@pytest.fixture
def dedup_store():
    """Create a fresh InMemoryDedup store."""
    return InMemoryDedup(window_seconds=300)


@pytest.mark.anyio
async def test_dispatch_route_calls_handler_for_item(dedup_store):
    """dispatch_route should call the handler for the item identified in resourceData."""
    called_with = []

    async def handler(item):
        called_with.append(item)

    item = _make_item(item_id="1")
    resource = _make_mock_resource({"1": item})
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=False)
    payload = _make_payload(VALID_NOTIFICATION)

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    assert dispatched == 1
    assert len(called_with) == 1
    assert called_with[0]["id"] == "1"
    resource.get_item.assert_called_once_with("1")


@pytest.mark.anyio
async def test_dispatch_route_handles_multiple_notifications(dedup_store):
    """dispatch_route should process each notification and fetch the corresponding item."""
    called_with = []

    async def handler(item):
        called_with.append(item)

    items = {
        "1": _make_item(item_id="1", last_modified="2026-02-23T12:00:00Z"),
        "2": _make_item(item_id="2", last_modified="2026-02-23T12:01:00Z"),
    }
    resource = _make_mock_resource(items)
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=False)
    payload = _make_payload(
        _make_notification(item_id="1"),
        _make_notification(item_id="2"),
    )

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    assert dispatched == 2
    assert len(called_with) == 2
    assert called_with[0]["id"] == "1"
    assert called_with[1]["id"] == "2"


@pytest.mark.anyio
async def test_dispatch_route_skips_wrong_client_state(dedup_store):
    """dispatch_route should not call handler when clientState doesn't match."""
    called_with = []

    async def handler(item):
        called_with.append(item)

    resource = _make_mock_resource()
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=False)
    payload = _make_payload(WRONG_STATE_NOTIFICATION)

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    assert dispatched == 0
    assert len(called_with) == 0
    resource.get_item.assert_not_called()


@pytest.mark.anyio
async def test_dispatch_route_skips_missing_resource_data(dedup_store):
    """dispatch_route should skip notifications without resourceData."""
    called_with = []

    async def handler(item):
        called_with.append(item)

    notification_no_rd = {k: v for k, v in VALID_NOTIFICATION.items() if k != "resourceData"}
    resource = _make_mock_resource()
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=False)
    payload = _make_payload(notification_no_rd)

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    assert dispatched == 0
    assert len(called_with) == 0
    resource.get_item.assert_not_called()


@pytest.mark.anyio
async def test_dispatch_route_filters_self_writes(dedup_store):
    """dispatch_route should skip items modified by the app when filter_self=True."""
    called_with = []

    async def handler(item):
        called_with.append(item)

    item = _make_item(item_id="1", modified_by_app=APP_IDENTITY)
    resource = _make_mock_resource({"1": item})
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=True)
    payload = _make_payload(VALID_NOTIFICATION)

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    assert dispatched == 0
    assert len(called_with) == 0


@pytest.mark.anyio
async def test_dispatch_route_no_self_filter_when_disabled(dedup_store):
    """dispatch_route should process app-modified items when filter_self=False."""
    called_with = []

    async def handler(item):
        called_with.append(item)

    item = _make_item(item_id="1", modified_by_app=APP_IDENTITY)
    resource = _make_mock_resource({"1": item})
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=False)
    payload = _make_payload(VALID_NOTIFICATION)

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    assert dispatched == 1


@pytest.mark.anyio
async def test_dispatch_route_item_level_dedup(dedup_store):
    """dispatch_route should not process the same item+timestamp twice."""
    call_count = 0

    async def handler(item):
        nonlocal call_count
        call_count += 1

    # Same item, same lastModifiedDateTime — two separate notifications
    item = _make_item(item_id="1", last_modified="2026-02-23T12:00:00Z")
    resource = _make_mock_resource({"1": item})
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=False)

    payload1 = _make_payload(_make_notification(item_id="1", subscriptionId="sub-1"))
    payload2 = _make_payload(_make_notification(item_id="1", subscriptionId="sub-2"))

    await dispatch_route(route, payload1, CONFIG, dedup_store)
    await dispatch_route(route, payload2, CONFIG, dedup_store)

    # Item dedup: same item + same timestamp -> handler called once
    assert call_count == 1


@pytest.mark.anyio
async def test_dispatch_route_processes_updated_item(dedup_store):
    """dispatch_route should process the same item again if its timestamp changes."""
    called_with = []

    async def handler(item):
        called_with.append(item)

    # First notification: item at time T1
    item_v1 = _make_item(item_id="1", last_modified="2026-02-23T12:00:00Z")
    resource = _make_mock_resource({"1": item_v1})
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=False)
    payload1 = _make_payload(_make_notification(item_id="1", subscriptionId="sub-1"))
    await dispatch_route(route, payload1, CONFIG, dedup_store)

    # Second notification: same item at time T2 (human edited again)
    item_v2 = _make_item(item_id="1", last_modified="2026-02-23T12:05:00Z")
    resource.get_item.side_effect = lambda item_id: item_v2
    payload2 = _make_payload(_make_notification(item_id="1", subscriptionId="sub-2"))
    await dispatch_route(route, payload2, CONFIG, dedup_store)

    # Both should be processed — different timestamps mean different edits
    assert len(called_with) == 2


@pytest.mark.anyio
async def test_dispatch_route_records_before_handler(dedup_store):
    """dispatch_route should record the item in dedup BEFORE calling the handler."""
    recorded_before_handler = []

    async def handler(item):
        key = f"item:/test:{item['id']}:{item['lastModifiedDateTime']}"
        # record_if_new returns False if the key was already recorded
        recorded_before_handler.append(dedup_store.record_if_new(key))

    item = _make_item()
    resource = _make_mock_resource({"1": item})
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=False)
    payload = _make_payload(VALID_NOTIFICATION)

    await dispatch_route(route, payload, CONFIG, dedup_store)

    # The handler should see the key as already recorded (False = duplicate)
    assert recorded_before_handler == [False]


@pytest.mark.anyio
async def test_dispatch_route_handles_get_item_failure(dedup_store):
    """dispatch_route should skip the item if get_item raises an exception."""

    async def handler(item):
        pass

    resource = MagicMock()
    resource.get_item.side_effect = RuntimeError("connection failed")
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=False)
    payload = _make_payload(VALID_NOTIFICATION)

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    assert dispatched == 0


@pytest.mark.anyio
async def test_dispatch_route_handles_handler_failure(dedup_store):
    """dispatch_route should continue processing other items if the handler fails for one."""
    called_with = []

    async def handler(item):
        if item["id"] == "1":
            raise RuntimeError("handler failed")
        called_with.append(item)

    items = {
        "1": _make_item(item_id="1"),
        "2": _make_item(item_id="2"),
    }
    resource = _make_mock_resource(items)
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=False)
    payload = _make_payload(
        _make_notification(item_id="1"),
        _make_notification(item_id="2"),
    )

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    # Item 1 failed, item 2 succeeded
    assert dispatched == 1
    assert called_with[0]["id"] == "2"


@pytest.mark.anyio
async def test_dispatch_route_empty_payload(dedup_store):
    """dispatch_route should handle an empty notification payload."""

    async def handler(item):
        pass

    resource = _make_mock_resource()
    route = WebhookRoute(path="/test", resource=resource, handler=handler, filter_self=False)
    payload = _make_payload()

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    assert dispatched == 0


# ============================================================================
# WebhookRoute Validation Tests
# ============================================================================


def test_route_path_must_start_with_slash():
    """WebhookRoute should reject paths that don't start with /."""

    async def handler(item):
        pass

    resource = _make_mock_resource()
    with pytest.raises(ValueError, match="must start with '/'"):
        WebhookRoute(path="no_slash", resource=resource, handler=handler)


def test_route_path_accepts_valid_path():
    """WebhookRoute should accept paths that start with /."""

    async def handler(item):
        pass

    resource = _make_mock_resource()
    route = WebhookRoute(path="/valid", resource=resource, handler=handler)
    assert route.path == "/valid"
