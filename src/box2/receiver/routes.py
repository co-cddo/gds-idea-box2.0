"""Webhook route configuration.

Defines the ``WebhookRoute`` dataclass used to declare endpoints in the
receiver app factory. Each route maps a URL path to a subscribable
resource and a handler that processes each changed item.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from box2.sharepoint.protocols import SubscribableResource


@dataclass
class WebhookRoute:
    """A webhook endpoint definition for the receiver app factory.

    Each route becomes a POST endpoint in the FastAPI app. When a notification
    arrives, the factory extracts the item ID from ``resourceData``, calls
    ``resource.get_item(item_id)`` to fetch the specific item, applies
    self-write filtering and item-level dedup, then calls ``handler(item)``.

    Attributes:
        path: URL path for this endpoint, e.g. ``"/file_uploaded"``.
            Must start with ``/``.
        resource: A subscribable SharePoint resource (e.g. ``ListClient`` or
            ``DocsClient``). Must satisfy the ``SubscribableResource`` protocol,
            which requires a ``get_item(item_id)`` method.
        handler: Async callable invoked once per matching item. Receives a
            single item dict (the full Graph API response with fields expanded).
        filter_self: If ``True``, items where ``lastModifiedBy.application.id``
            matches the config's ``app_identity`` are skipped. Set to ``False``
            for resources the app never writes to (e.g. a files list where
            only humans upload). Defaults to ``True``.

    Example::

        WebhookRoute(
            path="/file_uploaded",
            resource=docs_client,
            handler=process_new_file,
            filter_self=False,
        )
    """

    path: str
    resource: SubscribableResource
    handler: Callable[[dict[str, Any]], Awaitable[None]]
    filter_self: bool = field(default=True)

    def __post_init__(self) -> None:
        """Validate route configuration."""
        if not self.path.startswith("/"):
            raise ValueError(f"Route path must start with '/', got '{self.path}'")
