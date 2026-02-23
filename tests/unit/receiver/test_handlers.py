"""Unit tests for notification handler logic."""

import pytest

from box2.receiver.config import ReceiverConfig
from box2.receiver.dedup import InMemoryDedup
from box2.receiver.handlers import (
    build_item_dedup_key,
    build_notification_dedup_key,
    dispatch_route,
    filter_self_writes,
)
from box2.receiver.models import Notification, NotificationPayload
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
    "resource": "sites/site-id/lists/list-id",
    "tenantId": "tenant-id-999",
}

WRONG_STATE_NOTIFICATION = {
    "subscriptionId": "sub-abc-123",
    "changeType": "updated",
    "clientState": "wrong-secret",
    "resource": "sites/site-id/lists/list-id",
    "tenantId": "tenant-id-999",
}


def _make_item(
    item_id: str = "item-1",
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


# ============================================================================
# build_notification_dedup_key Tests
# ============================================================================


def test_notification_dedup_key_includes_subscription_resource_and_change_type():
    """Notification dedup key should combine subscription, resource, and change type."""
    notification = Notification.model_validate(VALID_NOTIFICATION)
    key = build_notification_dedup_key(notification)

    assert "sub-abc-123" in key
    assert "sites/site-id/lists/list-id" in key
    assert "updated" in key


def test_notification_dedup_key_differs_for_different_change_types():
    """Different change types on the same resource should produce different keys."""
    n1 = Notification.model_validate({**VALID_NOTIFICATION, "changeType": "updated"})
    n2 = Notification.model_validate({**VALID_NOTIFICATION, "changeType": "created"})

    assert build_notification_dedup_key(n1) != build_notification_dedup_key(n2)


# ============================================================================
# build_item_dedup_key Tests
# ============================================================================


def test_item_dedup_key_includes_id_and_timestamp():
    """Item dedup key should combine item ID and lastModifiedDateTime."""
    item = _make_item(item_id="item-42", last_modified="2026-02-23T12:30:00Z")
    key = build_item_dedup_key(item)

    assert "item-42" in key
    assert "2026-02-23T12:30:00Z" in key


def test_item_dedup_key_differs_for_same_item_different_timestamp():
    """Same item with a newer timestamp should produce a different key."""
    item_v1 = _make_item(item_id="item-1", last_modified="2026-02-23T12:00:00Z")
    item_v2 = _make_item(item_id="item-1", last_modified="2026-02-23T12:05:00Z")

    assert build_item_dedup_key(item_v1) != build_item_dedup_key(item_v2)


def test_item_dedup_key_same_for_identical_item_and_timestamp():
    """Same item with the same timestamp should produce the same key."""
    item_a = _make_item(item_id="item-1", last_modified="2026-02-23T12:00:00Z")
    item_b = _make_item(item_id="item-1", last_modified="2026-02-23T12:00:00Z")

    assert build_item_dedup_key(item_a) == build_item_dedup_key(item_b)


# ============================================================================
# filter_self_writes Tests
# ============================================================================


def test_filter_self_writes_removes_app_modified_items():
    """Items modified by the app's service principal should be filtered out."""
    items = [
        _make_item(item_id="1", modified_by_app=APP_IDENTITY),
        _make_item(item_id="2"),  # modified by human
    ]

    result = filter_self_writes(items, APP_IDENTITY)

    assert len(result) == 1
    assert result[0]["id"] == "2"


def test_filter_self_writes_keeps_human_modified_items():
    """Items modified by a human user should be kept."""
    items = [_make_item(item_id="1"), _make_item(item_id="2")]

    result = filter_self_writes(items, APP_IDENTITY)

    assert len(result) == 2


def test_filter_self_writes_keeps_items_with_different_app_id():
    """Items modified by a different app should not be filtered."""
    items = [_make_item(item_id="1", modified_by_app="other-app-id")]

    result = filter_self_writes(items, APP_IDENTITY)

    assert len(result) == 1


def test_filter_self_writes_handles_missing_lastmodifiedby():
    """Items without lastModifiedBy should be kept (not crash)."""
    item = {"id": "1", "lastModifiedDateTime": "2026-02-23T12:00:00Z", "fields": {}}

    result = filter_self_writes([item], APP_IDENTITY)

    assert len(result) == 1


def test_filter_self_writes_empty_list():
    """An empty item list should return an empty list."""
    result = filter_self_writes([], APP_IDENTITY)

    assert result == []


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
async def test_dispatch_route_calls_handler_for_each_item(dedup_store):
    """dispatch_route should call the handler once per matching item."""
    called_with = []

    async def handler(item):
        called_with.append(item)

    items = [_make_item(item_id="1"), _make_item(item_id="2")]
    route = WebhookRoute(path="/test", get_items=lambda: items, handler=handler, filter_self=False)
    payload = _make_payload(VALID_NOTIFICATION)

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

    items = [_make_item()]
    route = WebhookRoute(path="/test", get_items=lambda: items, handler=handler, filter_self=False)
    payload = _make_payload(WRONG_STATE_NOTIFICATION)

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    assert dispatched == 0
    assert len(called_with) == 0


@pytest.mark.anyio
async def test_dispatch_route_skips_duplicate_notification(dedup_store):
    """dispatch_route should not process the same notification twice."""
    call_count = 0

    async def handler(item):
        nonlocal call_count
        call_count += 1

    items = [_make_item()]
    route = WebhookRoute(path="/test", get_items=lambda: items, handler=handler, filter_self=False)
    payload = _make_payload(VALID_NOTIFICATION)

    await dispatch_route(route, payload, CONFIG, dedup_store)
    await dispatch_route(route, payload, CONFIG, dedup_store)

    # get_items returns the same item both times, but notification dedup
    # prevents the second invocation from querying items at all
    assert call_count == 1


@pytest.mark.anyio
async def test_dispatch_route_filters_self_writes(dedup_store):
    """dispatch_route should skip items modified by the app when filter_self=True."""
    called_with = []

    async def handler(item):
        called_with.append(item)

    items = [
        _make_item(item_id="app-wrote", modified_by_app=APP_IDENTITY),
        _make_item(item_id="human-wrote"),
    ]
    route = WebhookRoute(path="/test", get_items=lambda: items, handler=handler, filter_self=True)
    payload = _make_payload(VALID_NOTIFICATION)

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    assert dispatched == 1
    assert called_with[0]["id"] == "human-wrote"


@pytest.mark.anyio
async def test_dispatch_route_no_self_filter_when_disabled(dedup_store):
    """dispatch_route should process all items when filter_self=False."""
    called_with = []

    async def handler(item):
        called_with.append(item)

    items = [_make_item(item_id="app-wrote", modified_by_app=APP_IDENTITY)]
    route = WebhookRoute(path="/test", get_items=lambda: items, handler=handler, filter_self=False)
    payload = _make_payload(VALID_NOTIFICATION)

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    assert dispatched == 1


@pytest.mark.anyio
async def test_dispatch_route_item_level_dedup(dedup_store):
    """dispatch_route should not process the same item+timestamp twice across notifications."""
    call_count = 0

    async def handler(item):
        nonlocal call_count
        call_count += 1

    # Same item with same lastModifiedDateTime
    items = [_make_item(item_id="1", last_modified="2026-02-23T12:00:00Z")]
    route = WebhookRoute(path="/test", get_items=lambda: items, handler=handler, filter_self=False)

    # First notification — use unique subscription IDs so notification-level dedup doesn't trigger
    payload1 = _make_payload({**VALID_NOTIFICATION, "subscriptionId": "sub-1"})
    payload2 = _make_payload({**VALID_NOTIFICATION, "subscriptionId": "sub-2"})

    await dispatch_route(route, payload1, CONFIG, dedup_store)
    await dispatch_route(route, payload2, CONFIG, dedup_store)

    # Item should be processed only once — item-level dedup catches the second
    assert call_count == 1


@pytest.mark.anyio
async def test_dispatch_route_processes_updated_item(dedup_store):
    """dispatch_route should process the same item again if its timestamp changes."""
    called_with = []

    async def handler(item):
        called_with.append(item)

    route = WebhookRoute(
        path="/test",
        get_items=lambda: [],  # overridden below
        handler=handler,
        filter_self=False,
    )

    # First notification with item at time T1
    items_v1 = [_make_item(item_id="1", last_modified="2026-02-23T12:00:00Z")]
    route.get_items = lambda: items_v1
    payload1 = _make_payload({**VALID_NOTIFICATION, "subscriptionId": "sub-1"})
    await dispatch_route(route, payload1, CONFIG, dedup_store)

    # Second notification with same item at time T2 (human edited it again)
    items_v2 = [_make_item(item_id="1", last_modified="2026-02-23T12:05:00Z")]
    route.get_items = lambda: items_v2
    payload2 = _make_payload({**VALID_NOTIFICATION, "subscriptionId": "sub-2"})
    await dispatch_route(route, payload2, CONFIG, dedup_store)

    # Both should be processed — different timestamps mean different edits
    assert len(called_with) == 2


@pytest.mark.anyio
async def test_dispatch_route_records_before_handler(dedup_store):
    """dispatch_route should record the item in dedup BEFORE calling the handler."""
    recorded_before_handler = []

    async def handler(item):
        key = f"item:{item['id']}:{item['lastModifiedDateTime']}"
        recorded_before_handler.append(dedup_store.is_duplicate(key))

    items = [_make_item()]
    route = WebhookRoute(path="/test", get_items=lambda: items, handler=handler, filter_self=False)
    payload = _make_payload(VALID_NOTIFICATION)

    await dispatch_route(route, payload, CONFIG, dedup_store)

    # The handler should see the key as already recorded (True = duplicate)
    assert recorded_before_handler == [True]


@pytest.mark.anyio
async def test_dispatch_route_handles_get_items_failure(dedup_store):
    """dispatch_route should return 0 if get_items raises an exception."""

    async def handler(item):
        pass

    def failing_get_items():
        raise RuntimeError("connection failed")

    route = WebhookRoute(path="/test", get_items=failing_get_items, handler=handler, filter_self=False)
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

    items = [_make_item(item_id="1"), _make_item(item_id="2")]
    route = WebhookRoute(path="/test", get_items=lambda: items, handler=handler, filter_self=False)
    payload = _make_payload(VALID_NOTIFICATION)

    dispatched = await dispatch_route(route, payload, CONFIG, dedup_store)

    # Item 1 failed, item 2 succeeded
    assert dispatched == 1
    assert called_with[0]["id"] == "2"


@pytest.mark.anyio
async def test_dispatch_route_empty_payload(dedup_store):
    """dispatch_route should handle an empty notification payload."""

    async def handler(item):
        pass

    route = WebhookRoute(path="/test", get_items=lambda: [], handler=handler, filter_self=False)
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

    with pytest.raises(ValueError, match="must start with '/'"):
        WebhookRoute(path="no_slash", get_items=lambda: [], handler=handler)


def test_route_path_accepts_valid_path():
    """WebhookRoute should accept paths that start with /."""

    async def handler(item):
        pass

    route = WebhookRoute(path="/valid", get_items=lambda: [], handler=handler)
    assert route.path == "/valid"
