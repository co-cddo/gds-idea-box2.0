"""Receiver configuration.

Centralised configuration for the webhook receiver. Uses Pydantic for
validation so that misconfigured deployments fail fast at startup.
"""

from pydantic import BaseModel, Field


class ReceiverConfig(BaseModel):
    """Configuration for the webhook receiver.

    Attributes:
        client_state: Shared secret that Microsoft sends with each notification.
            The receiver rejects any notification whose ``clientState`` does not
            match this value.
        dedup_window_seconds: Time window (in seconds) during which duplicate
            notifications for the same resource change are suppressed.
            Defaults to 300 (5 minutes).
    """

    client_state: str = Field(min_length=1, description="Shared secret for notification validation")
    dedup_window_seconds: int = Field(default=300, gt=0, description="Deduplication window in seconds")
