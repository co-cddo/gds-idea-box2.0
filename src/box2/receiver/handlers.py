"""Notification processing and item handling logic.

Provides the per-request pipeline that runs after a notification arrives:
client-state validation, item fetch by ID (from ``resourceData``),
self-write filtering, item-level dedup, and handler invocation.

The ``dispatch_route`` function orchestrates this pipeline for a single
route.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from box2.receiver.config import ReceiverConfig
from box2.receiver.dedup import DeduplicationStore, build_item_dedup_key
from box2.receiver.models import Notification, NotificationPayload
from box2.receiver.routes import WebhookRoute

logger = logging.getLogger(__name__)


def _is_self_write(item: dict[str, Any], app_identity: str) -> bool:
    """Check whether an item was last modified by the application itself.

    Inspects the ``lastModifiedBy.application.id`` field on the item.

    Args:
        item: An item dict from the Graph API.
        app_identity: The Azure AD application ID of this backend.

    Returns:
        ``True`` if the item was modified by the app, ``False`` otherwise.
    """
    modified_by = item.get("lastModifiedBy", {})
    app_info = modified_by.get("application", {})
    return app_info.get("id") == app_identity


async def dispatch_route(
    route: WebhookRoute,
    payload: NotificationPayload,
    config: ReceiverConfig,
    dedup_store: DeduplicationStore,
) -> int:
    """Process a notification payload for a specific route.

    Implements the per-request pipeline for each notification in the payload:

    1. Validate ``clientState`` — skip if mismatch.
    2. Extract ``resource_data.id`` from the notification — skip if absent.
    3. Call ``route.resource.get_item(item_id)`` to fetch the specific item.
    4. If ``route.filter_self`` is True, skip items modified by the app.
    5. Item-level dedup — atomically record the item in the dedup store
       and skip duplicates (at-most-once semantics).
    6. Call ``route.handler(item)`` for the remaining item.

    Args:
        route: The webhook route being processed.
        payload: The parsed notification payload from Microsoft Graph.
        config: Receiver configuration.
        dedup_store: Store for item-level deduplication.

    Returns:
        The number of items that were dispatched to the handler.
    """
    dispatched = 0

    for notification in payload.value:
        # Step 1: validate clientState
        if notification.client_state != config.client_state:
            logger.warning(
                "clientState mismatch (subscription=%s, resource=%s) — skipping",
                notification.subscription_id,
                notification.resource,
            )
            continue

        _log_notification(notification)

        # Step 2: extract item ID from resourceData
        resource_data = notification.resource_data
        if not resource_data or not resource_data.id:
            logger.warning(
                "Notification missing resourceData.id (subscription=%s, resource=%s) — skipping",
                notification.subscription_id,
                notification.resource,
            )
            continue

        item_id = resource_data.id
        logger.debug(
            "Extracted item_id=%s from resourceData (odata_id=%s)",
            item_id,
            resource_data.odata_id,
        )

        # Step 3: fetch the specific item
        try:
            item = route.resource.get_item(item_id)
        except Exception:
            logger.exception("Failed to fetch item %s for route %s", item_id, route.path)
            continue

        logger.debug("Fetched item %s for route %s", item_id, route.path)

        # Step 4: filter self-writes
        if route.filter_self:
            if _is_self_write(item, config.app_identity):
                logger.info(
                    "Skipping self-modified item (id=%s, lastModifiedBy=%s) on route %s",
                    item.get("id"),
                    config.app_identity,
                    route.path,
                )
                continue
            logger.debug("Item %s passed self-write filter on route %s", item_id, route.path)

        # Step 5: item-level dedup
        item_key = build_item_dedup_key(route.path, item)
        is_new = dedup_store.record_if_new(item_key)
        logger.debug("Item dedup: key=%s, is_new=%s", item_key, is_new)

        if not is_new:
            logger.info("Skipping already-processed item (key=%s)", item_key)
            continue

        # Step 6: call handler
        try:
            await route.handler(item)
            dispatched += 1
            logger.debug("Handler dispatched for item %s on route %s", item_id, route.path)
        except Exception:
            logger.exception("Handler failed for item %s on route %s", item_id, route.path)

    logger.info("Route %s: dispatched %d item(s) to handler", route.path, dispatched)
    return dispatched


def _log_notification(notification: Notification) -> None:
    """Log a received notification with a prominent banner.

    Args:
        notification: The notification to log.
    """
    received_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    resource_id = None
    if notification.resource_data:
        resource_id = notification.resource_data.id

    banner = (
        "\n"
        "============================================================\n"
        "  NOTIFICATION RECEIVED\n"
        f"    Subscription:  {notification.subscription_id}\n"
        f"    Resource:      {notification.resource}\n"
        f"    Resource ID:   {resource_id}\n"
        f"    Change Type:   {notification.change_type}\n"
        f"    Tenant:        {notification.tenant_id}\n"
        f"    Received At:   {received_at}\n"
        "============================================================"
    )
    logger.info(banner)
