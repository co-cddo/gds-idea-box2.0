"""Route-specific handler factories for the box2 receiver.

Each ``make_*_handler`` factory accepts the clients it needs and returns
an ``async def handler(item: dict) -> None`` matching the signature
expected by :class:`~box2.receiver.routes.WebhookRoute`.

Usage in ``lambda_handler.py``::

    handle_new_file = make_file_upload_handler(
        docs=docs,
        invitation_list=invitation_list,
        submission_list=submission_list,
    )

    WebhookRoute(
        path="/file_uploaded",
        get_items=lambda: docs.get_recent(minutes=2),
        handler=handle_new_file,
        ...
    )
"""

import logging
import os
from collections.abc import Awaitable, Callable

from box2.pipeline import (
    TriagedInvitation,
    to_sharepoint_fields,
    to_sharepoint_invitation,
    to_sharepoint_submission,
    triage_file,
)
from box2.sharepoint import DocsClient, ListClient
from box2.triage.models import Submission

logger = logging.getLogger(__name__)


def make_file_upload_handler(
    docs: DocsClient,
    invitation_list: ListClient,
    submission_list: ListClient,
    download_dir: str = "/tmp/downloads",
) -> Callable[[dict], Awaitable[None]]:
    """Create a handler for newly uploaded files.

    Downloads the file from SharePoint, runs the triage pipeline, maps
    the result to the appropriate SharePoint list schema, and writes it.

    Args:
        docs: DocsClient for downloading files from SharePoint.
        invitation_list: ListClient for the invitations SharePoint list.
        submission_list: ListClient for the submissions SharePoint list.
        download_dir: Local directory for temporary file downloads.
            Defaults to ``/tmp/downloads`` (Lambda-friendly).

    Returns:
        An async handler function matching the WebhookRoute signature.
    """

    async def handle_new_file(item: dict) -> None:
        """Process a newly uploaded file through the triage pipeline."""
        name = item.get("name", "unknown")
        item_id = item.get("id", "unknown")
        logger.info(f"Processing new file: {name} (id={item_id})")

        local_path = docs.download_file(item, download_dir=download_dir)

        try:
            result = await triage_file(local_path)

            match result:
                case TriagedInvitation():
                    fields = to_sharepoint_fields(to_sharepoint_invitation(result))
                    invitation_list.create_item(fields)
                    logger.info(f"Wrote triaged invitation to '{invitation_list.list_name}' for {name}")

                case Submission():
                    fields = to_sharepoint_fields(to_sharepoint_submission(result))
                    submission_list.create_item(fields)
                    logger.info(f"Wrote submission to '{submission_list.list_name}' for {name}")

                case _:
                    logger.info(f"No list write for {name}: result type={type(result).__name__}")
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.debug(f"Cleaned up {local_path}")

    return handle_new_file
