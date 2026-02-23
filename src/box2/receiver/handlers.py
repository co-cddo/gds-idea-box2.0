"""Notification processing and item handling logic.

Provides the per-request pipeline that runs after a notification arrives:
notification-level dedup, item querying, self-write filtering, item-level
dedup, and handler invocation.

The ``dispatch_route`` function orchestrates this pipeline for a single
route. Placeholder handler functions log what would be processed — real
workflow implementations will replace these later.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from box2.receiver.config import ReceiverConfig
from box2.receiver.dedup import DeduplicationStore
from box2.receiver.models import Notification, NotificationPayload
from box2.receiver.routes import WebhookRoute

logger = logging.getLogger(__name__)


def build_notification_dedup_key(notification: Notification) -> str:
    """Build a deduplication key from a notification.

    The key combines subscription ID, resource, and change type so that
    different change types on the same resource are treated independently.

    Args:
        notification: The notification to build a key for.

    Returns:
        A string key suitable for deduplication lookups.
    """
    return f"notif:{notification.subscription_id}:{notification.resource}:{notification.change_type}"


def build_item_dedup_key(item: dict[str, Any]) -> str:
    """Build a deduplication key for a list/drive item.

    The key combines the item ID and its ``lastModifiedDateTime`` so that
    the same edit is not processed twice, but a new edit on the same item
    (with a newer timestamp) is treated as a fresh event.

    Args:
        item: An item dict as returned by the Graph API.

    Returns:
        A string key suitable for deduplication lookups.
    """
    item_id = item.get("id", "unknown")
    modified = item.get("lastModifiedDateTime", "unknown")
    return f"item:{item_id}:{modified}"


def filter_self_writes(items: list[dict[str, Any]], app_identity: str) -> list[dict[str, Any]]:
    """Remove items last modified by the application's own service principal.

    Checks the ``lastModifiedBy.application.id`` field on each item. Items
    modified by the app are dropped to avoid self-triggered processing loops.

    Args:
        items: List of item dicts from the Graph API.
        app_identity: The Azure AD application ID of this backend.

    Returns:
        Filtered list with self-modified items removed.
    """
    filtered = []
    for item in items:
        modified_by = item.get("lastModifiedBy", {})
        app_info = modified_by.get("application", {})
        if app_info.get("id") == app_identity:
            logger.info(
                "Skipping self-modified item (id=%s, lastModifiedBy=%s)",
                item.get("id"),
                app_identity,
            )
            continue
        filtered.append(item)
    return filtered


async def dispatch_route(
    route: WebhookRoute,
    payload: NotificationPayload,
    config: ReceiverConfig,
    dedup_store: DeduplicationStore,
) -> int:
    """Process a notification payload for a specific route.

    Implements the full per-request pipeline:

    1. Validate ``clientState`` on each notification.
    2. Notification-level dedup — skip already-seen notifications.
    3. Call ``route.get_items()`` to fetch candidate items.
    4. If ``route.filter_self`` is True, remove items modified by the app.
    5. Item-level dedup — skip items already processed.
    6. Record each item in the dedup store *before* calling the handler
       (at-most-once semantics).
    7. Call ``route.handler(item)`` for each remaining item.

    Args:
        route: The webhook route being processed.
        payload: The parsed notification payload from Microsoft Graph.
        config: Receiver configuration.
        dedup_store: Store for both notification and item deduplication.

    Returns:
        The number of items that were dispatched to the handler.
    """
    # Step 1 & 2: validate and dedup notifications
    valid_notifications = 0
    for notification in payload.value:
        if notification.client_state != config.client_state:
            logger.warning(
                "clientState mismatch (subscription=%s, resource=%s) — skipping",
                notification.subscription_id,
                notification.resource,
            )
            continue

        key = build_notification_dedup_key(notification)
        if dedup_store.is_duplicate(key):
            logger.info(
                "Duplicate notification (subscription=%s, resource=%s) — skipping",
                notification.subscription_id,
                notification.resource,
            )
            continue

        dedup_store.record(key)
        valid_notifications += 1
        _log_notification(notification)

    if valid_notifications == 0:
        return 0

    # Step 3: fetch candidate items
    try:
        items = route.get_items()
    except Exception:
        logger.exception("Failed to fetch items for route %s", route.path)
        return 0

    logger.info("Route %s: fetched %d candidate item(s)", route.path, len(items))

    # Step 4: filter self-writes
    if route.filter_self:
        items = filter_self_writes(items, config.app_identity)
        logger.info("Route %s: %d item(s) after self-write filtering", route.path, len(items))

    # Step 5, 6, 7: item-level dedup, record, and dispatch
    dispatched = 0
    for item in items:
        item_key = build_item_dedup_key(item)
        if dedup_store.is_duplicate(item_key):
            logger.info("Skipping already-processed item (key=%s)", item_key)
            continue

        # Record before handler (at-most-once)
        dedup_store.record(item_key)

        try:
            await route.handler(item)
            dispatched += 1
        except Exception:
            logger.exception("Handler failed for item %s on route %s", item.get("id"), route.path)

    logger.info("Route %s: dispatched %d item(s) to handler", route.path, dispatched)
    return dispatched


def _log_notification(notification: Notification) -> None:
    """Log a received notification with a prominent banner.

    Args:
        notification: The notification to log.
    """
    received_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    banner = (
        "\n"
        "============================================================\n"
        "  NOTIFICATION RECEIVED\n"
        f"    Subscription:  {notification.subscription_id}\n"
        f"    Resource:      {notification.resource}\n"
        f"    Change Type:   {notification.change_type}\n"
        f"    Tenant:        {notification.tenant_id}\n"
        f"    Received At:   {received_at}\n"
        "============================================================"
    )
    logger.info(banner)
