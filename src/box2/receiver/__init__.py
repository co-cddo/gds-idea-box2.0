"""box2.receiver — FastAPI webhook receiver for Microsoft Graph notifications.

This is an optional submodule. Install with ``pip install box2[receiver]``
to get FastAPI and uvicorn dependencies.

Usage::

    from box2.receiver import create_app
    from box2.receiver.config import ReceiverConfig

    config = ReceiverConfig(client_state="my-shared-secret")
    app = create_app(config)
"""

from box2.receiver.app import create_app
from box2.receiver.config import ReceiverConfig
from box2.receiver.dedup import DeduplicationStore, InMemoryDedup
from box2.receiver.models import Notification, NotificationPayload

__all__ = [
    "create_app",
    "ReceiverConfig",
    "DeduplicationStore",
    "InMemoryDedup",
    "Notification",
    "NotificationPayload",
]
