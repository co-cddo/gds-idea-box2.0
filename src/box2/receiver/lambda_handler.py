"""AWS Lambda entry point for the box2 webhook receiver.

Wraps the FastAPI app with Mangum so API Gateway can invoke it as a
Lambda function. Wires up a single ``/file_uploaded`` route backed by
a real ``DocsClient`` (authenticated via environment variables).

The handler placeholder logs what it receives — real workflow wiring
comes later.

Environment variables (required):
    CLIENT_STATE             — shared secret for notification validation
    APP_IDENTITY             — Azure AD service principal app ID
    DYNAMO_TABLE_NAME        — DynamoDB table for deduplication
    SHAREPOINT_TENANT_ID     — Azure AD tenant ID
    SHAREPOINT_CLIENT_ID     — Azure AD app registration client ID
    SHAREPOINT_SITE_HOST     — e.g. contoso.sharepoint.com
    SHAREPOINT_SITE_PATH     — e.g. /sites/my-site
    SHAREPOINT_ROLE_ARN      — IAM role ARN for STS assume-role

Environment variables (optional):
    LOOKBACK_MINUTES         — rolling window for get_recent (default: 2)
    DEDUP_WINDOW_SECONDS     — dedup TTL in seconds (default: 300)
    DOCS_LIBRARY_NAME        — document library name (default: Documents)
    AWS_REGION               — AWS region for STS (default: eu-west-2)

Deployment:
    Configure the Lambda handler as ``box2.receiver.lambda_handler.handler``.
    API Gateway should proxy all requests to the Lambda function.
"""

import logging
import os

from mangum import Mangum

from box2.receiver import ReceiverConfig, WebhookRoute, create_app
from box2.receiver.dedup import DynamoDedup
from box2.sharepoint import DocsClient, SharePointSession

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration from environment
# ============================================================================

CLIENT_STATE = os.environ["CLIENT_STATE"]
APP_IDENTITY = os.environ["APP_IDENTITY"]
DYNAMO_TABLE_NAME = os.environ["DYNAMO_TABLE_NAME"]
LOOKBACK_MINUTES = int(os.environ.get("LOOKBACK_MINUTES", "2"))
DEDUP_WINDOW_SECONDS = int(os.environ.get("DEDUP_WINDOW_SECONDS", "300"))
DOCS_LIBRARY_NAME = os.environ.get("DOCS_LIBRARY_NAME", "Documents")

# ============================================================================
# SharePoint session and client (created once per cold start)
# ============================================================================

session = SharePointSession.from_env()
docs = DocsClient(session, library_name=DOCS_LIBRARY_NAME)
dedup_store = DynamoDedup(table_name=DYNAMO_TABLE_NAME, window_seconds=DEDUP_WINDOW_SECONDS)

logger.info(
    "Lambda cold start: session=%s:%s, library=%s, lookback=%dm, dedup_table=%s",
    session.site_host,
    session.site_path,
    DOCS_LIBRARY_NAME,
    LOOKBACK_MINUTES,
    DYNAMO_TABLE_NAME,
)


# ============================================================================
# Placeholder handler — logs what would be processed
# ============================================================================


async def handle_new_file(item: dict) -> None:
    """Placeholder handler for newly uploaded files.

    Logs file metadata. Will be replaced with the real triage +
    extraction pipeline in a future PR.

    Args:
        item: A drive item dict from the Graph API delta response.
    """
    name = item.get("name", "unknown")
    item_id = item.get("id", "unknown")
    web_url = item.get("webUrl", "")
    size = item.get("size", 0)
    modified = item.get("lastModifiedDateTime", "unknown")

    banner = (
        "\n"
        "============================================================\n"
        "  NEW FILE UPLOADED\n"
        f"    Item ID:    {item_id}\n"
        f"    Name:       {name}\n"
        f"    Size:       {size} bytes\n"
        f"    Modified:   {modified}\n"
        f"    URL:        {web_url}\n"
        "\n"
        "    TODO: run triage + extraction pipeline\n"
        "============================================================"
    )
    logger.info(banner)


# ============================================================================
# FastAPI app + Mangum handler
# ============================================================================

config = ReceiverConfig(
    client_state=CLIENT_STATE,
    app_identity=APP_IDENTITY,
)

app = create_app(
    config=config,
    routes=[
        WebhookRoute(
            path="/file_uploaded",
            get_items=lambda: docs.get_recent(minutes=LOOKBACK_MINUTES),
            handler=handle_new_file,
            filter_self=False,
        ),
    ],
    dedup_store=dedup_store,
)

handler = Mangum(app, lifespan="off")
