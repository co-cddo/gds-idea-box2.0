"""AWS Lambda entry point for the box2 webhook receiver.

Wraps the FastAPI app with Mangum so API Gateway can invoke it as a
Lambda function. Wires up routes for file uploads and list item reviews
that run the triage pipeline and write results to SharePoint lists.

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
    INVITATION_LIST_NAME     — SharePoint invitation list (default: Invitations)
    SUBMISSION_LIST_NAME     — SharePoint submission list (default: Submissions)
    ACTIONS_LIST_NAME        — SharePoint actions list (default: Actions)
    QA_INVITATION_LIST_NAME  — QA invitations list (default: QA Invitations)
    REJECTED_INVITATION_LIST_NAME — rejected invitations list (default: Rejected Invitations)
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
from box2.receiver.route_handlers import make_file_upload_handler, make_list_review_handler, make_qa_review_handler
from box2.sharepoint import DocsClient, ListClient, SharePointSession

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
INVITATION_LIST_NAME = os.environ.get("INVITATION_LIST_NAME", "Invitations")
SUBMISSION_LIST_NAME = os.environ.get("SUBMISSION_LIST_NAME", "Submissions")
ACTIONS_LIST_NAME = os.environ.get("ACTIONS_LIST_NAME", "Actions")
QA_INVITATION_LIST_NAME = os.environ.get("QA_INVITATION_LIST_NAME", "QA_Invitations")
REJECTED_INVITATION_LIST_NAME = os.environ.get("REJECTED_INVITATION_LIST_NAME", "Rejected_Invitations")

# ============================================================================
# SharePoint session and clients (created once per cold start)
# ============================================================================

session = SharePointSession.from_env()
docs = DocsClient(session, library_name=DOCS_LIBRARY_NAME)
invitation_list = ListClient(session, list_name=INVITATION_LIST_NAME)
submission_list = ListClient(session, list_name=SUBMISSION_LIST_NAME)
actions_list = ListClient(session, list_name=ACTIONS_LIST_NAME)
qa_invitation_list = ListClient(session, list_name=QA_INVITATION_LIST_NAME)
rejected_invitation_list = ListClient(session, list_name=REJECTED_INVITATION_LIST_NAME)
dedup_store = DynamoDedup(table_name=DYNAMO_TABLE_NAME, window_seconds=DEDUP_WINDOW_SECONDS)

logger.info(
    f"Lambda cold start: session={session.site_host}:{session.site_path}, "
    f"library={DOCS_LIBRARY_NAME}, lookback={LOOKBACK_MINUTES}m, dedup_table={DYNAMO_TABLE_NAME}"
)


# ============================================================================
# Route handlers
# ============================================================================

handle_new_file = make_file_upload_handler(
    docs=docs,
    qa_invitation_list=qa_invitation_list,
    submission_list=submission_list,
)

handle_submission_review = make_list_review_handler(
    actions_list=actions_list,
    document_type="submission",
)

handle_invitation_review = make_list_review_handler(
    actions_list=actions_list,
    document_type="invitation",
)

handle_qa_review = make_qa_review_handler(
    invitation_list=invitation_list,
    rejected_list=rejected_invitation_list,
    qa_list=qa_invitation_list,
)


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
        WebhookRoute(
            path="/submission_reviewed",
            get_items=lambda: submission_list.get_recent(minutes=LOOKBACK_MINUTES),
            handler=handle_submission_review,
            filter_self=True,
        ),
        WebhookRoute(
            path="/invitation_reviewed",
            get_items=lambda: invitation_list.get_recent(minutes=LOOKBACK_MINUTES),
            handler=handle_invitation_review,
            filter_self=True,
        ),
        WebhookRoute(
            path="/qa_reviewed",
            get_items=lambda: qa_invitation_list.get_recent(minutes=LOOKBACK_MINUTES),
            handler=handle_qa_review,
            filter_self=True,
        ),
    ],
    dedup_store=dedup_store,
)

handler = Mangum(app, lifespan="off")
