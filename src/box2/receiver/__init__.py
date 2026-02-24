"""box2.receiver — FastAPI webhook receiver for Microsoft Graph notifications.

This is an optional submodule. Install with ``pip install box2[receiver]``
to get FastAPI and uvicorn dependencies.

Usage::

    from box2.receiver import create_app, ReceiverConfig, WebhookRoute

    config = ReceiverConfig(
        client_state="my-shared-secret",
        app_identity="<service-principal-app-id>",
    )

    app = create_app(
        config=config,
        routes=[
            WebhookRoute(
                path="/file_uploaded",
                get_items=lambda: docs.get_recent(minutes=2),
                handler=process_new_file,
                filter_self=False,
            ),
        ],
    )
"""

from box2.receiver.app import create_app
from box2.receiver.config import ReceiverConfig
from box2.receiver.dedup import (
    DeduplicationStore,
    DynamoDedup,
    InMemoryDedup,
    build_item_dedup_key,
    build_notification_dedup_key,
)
from box2.receiver.models import Notification, NotificationPayload
from box2.receiver.routes import WebhookRoute

__all__ = [
    "create_app",
    "ReceiverConfig",
    "WebhookRoute",
    "DeduplicationStore",
    "DynamoDedup",
    "InMemoryDedup",
    "build_notification_dedup_key",
    "build_item_dedup_key",
    "Notification",
    "NotificationPayload",
]
