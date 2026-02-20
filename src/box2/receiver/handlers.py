"""Notification processing logic.

Business logic for handling incoming Microsoft Graph change notifications.
Each notification is validated (client_state check), deduplicated, and
dispatched to the appropriate handler. The dispatch function is a placeholder
that will be wired to triage workflows later.
"""

import logging

from box2.receiver.config import ReceiverConfig
from box2.receiver.dedup import DeduplicationStore
from box2.receiver.models import Notification, NotificationPayload

logger = logging.getLogger(__name__)


def build_dedup_key(notification: Notification) -> str:
    """Build a deduplication key from a notification.

    The key combines subscription ID, resource, and change type so that
    different change types on the same resource are treated independently.

    Args:
        notification: The notification to build a key for.

    Returns:
        A string key suitable for deduplication lookups.
    """
    return f"{notification.subscription_id}:{notification.resource}:{notification.change_type}"


def process_notifications(
    payload: NotificationPayload,
    config: ReceiverConfig,
    dedup_store: DeduplicationStore,
) -> int:
    """Process a batch of notifications from Microsoft Graph.

    Iterates through the notification payload, validates each notification's
    ``clientState``, checks for duplicates, and dispatches valid notifications.

    Args:
        payload: The parsed notification payload from Microsoft Graph.
        config: Receiver configuration (client_state for validation, etc.).
        dedup_store: Store for deduplication checks.

    Returns:
        The number of notifications that were successfully dispatched
        (i.e. not skipped due to client_state mismatch or deduplication).
    """
    dispatched = 0

    for notification in payload.value:
        # Validate client_state
        if notification.client_state != config.client_state:
            logger.warning(
                "clientState mismatch (subscription=%s, resource=%s) — skipping",
                notification.subscription_id,
                notification.resource,
            )
            continue

        # Check for duplicates
        key = build_dedup_key(notification)
        if dedup_store.is_duplicate(key):
            logger.info(
                "Duplicate notification (subscription=%s, resource=%s) — skipping",
                notification.subscription_id,
                notification.resource,
            )
            continue

        # Record and dispatch
        dedup_store.record(key)
        dispatch(notification)
        dispatched += 1

    return dispatched


def dispatch(notification: Notification) -> None:
    """Dispatch a validated, deduplicated notification for processing.

    This is a placeholder that logs the notification. It will be replaced
    with triage workflow dispatch logic later.

    Args:
        notification: The notification to dispatch.
    """
    logger.info(
        "Dispatching notification: subscription=%s, resource=%s, change_type=%s",
        notification.subscription_id,
        notification.resource,
        notification.change_type,
    )
