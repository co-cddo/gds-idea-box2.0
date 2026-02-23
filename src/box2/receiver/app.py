"""FastAPI webhook receiver application.

Provides a factory function that creates a configured FastAPI app for
receiving Microsoft Graph change notifications. The app handles the
validation handshake and notification processing.

Usage::

    from box2.receiver import create_app
    from box2.receiver.config import ReceiverConfig

    config = ReceiverConfig(client_state="my-shared-secret")
    app = create_app(config)

    # Run with: uvicorn box2.receiver.app:app
    # Or programmatically: uvicorn.run(app, host="0.0.0.0", port=5000)
"""

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from box2.receiver.config import ReceiverConfig
from box2.receiver.dedup import DeduplicationStore, InMemoryDedup
from box2.receiver.handlers import process_notifications
from box2.receiver.models import NotificationPayload

logger = logging.getLogger(__name__)


def create_app(
    config: ReceiverConfig,
    dedup_store: DeduplicationStore | None = None,
) -> FastAPI:
    """Create a configured FastAPI webhook receiver.

    Args:
        config: Receiver configuration (client_state, dedup window, etc.).
        dedup_store: Optional deduplication store. If not provided, an
            ``InMemoryDedup`` is created using the config's dedup window.

    Returns:
        A FastAPI application instance with webhook and health routes.
    """
    if dedup_store is None:
        dedup_store = InMemoryDedup(window_seconds=config.dedup_window_seconds)

    app = FastAPI(title="box2 Webhook Receiver", docs_url=None, redoc_url=None)

    def get_config() -> ReceiverConfig:
        return config

    def get_dedup_store() -> DeduplicationStore:
        return dedup_store

    @app.post("/webhook")
    async def webhook(
        request: Request,
        receiver_config: Annotated[ReceiverConfig, Depends(get_config)],
        store: Annotated[DeduplicationStore, Depends(get_dedup_store)],
    ) -> Response:
        """Handle Microsoft Graph webhook notifications.

        This endpoint serves two purposes:

        1. **Validation handshake** — When Microsoft creates a subscription,
           it sends a request with a ``validationToken`` query parameter.
           The receiver must echo this token back as ``text/plain``.

        2. **Change notifications** — Microsoft POSTs a JSON payload
           containing one or more notifications about resource changes.
        """
        # Validation handshake
        validation_token = request.query_params.get("validationToken")
        if validation_token:
            logger.info("Validation handshake received — echoing token")
            return PlainTextResponse(content=validation_token, status_code=200)

        # Parse notification payload
        body = await request.json()
        if not body:
            return JSONResponse(content={"status": "no data"}, status_code=400)

        payload = NotificationPayload.model_validate(body)
        dispatched = process_notifications(payload, receiver_config, store)
        logger.info("Processed %d notification(s)", dispatched)

        return JSONResponse(content={"status": "accepted"}, status_code=202)

    @app.get("/health")
    async def health() -> dict:
        """Health check endpoint."""
        return {"status": "ok"}

    return app
