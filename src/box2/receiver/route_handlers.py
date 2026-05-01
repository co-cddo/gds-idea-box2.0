"""Route-specific handler factories for the box2 receiver.

Each ``make_*_handler`` factory accepts the clients it needs and returns
an ``async def handler(item: dict) -> None`` matching the signature
expected by :class:`~box2.receiver.routes.WebhookRoute`.

Usage in ``lambda_handler.py``::

    handle_new_file = make_file_upload_handler(
        docs=docs,
        qa_invitation_list=qa_invitation_list,
        submission_list=submission_list,
    )

    handle_submission_review = make_list_review_handler(
        actions_list=actions_list,
        document_type="submission",
    )

    handle_qa_review = make_qa_review_handler(
        invitation_list=invitation_list,
        rejected_list=rejected_list,
        qa_list=qa_invitation_list,
    )
"""

import logging
import os
from collections.abc import Awaitable, Callable
from typing import Literal

from box2.pipeline import (
    TriagedInvitation,
    extract_actions_from_review,
    from_sharepoint_fields,
    to_sharepoint_action,
    to_sharepoint_fields,
    to_sharepoint_invitation,
    to_sharepoint_invitation_qa,
    to_sharepoint_submission,
    triage_file,
)
from box2.sharepoint import DocsClient, ListClient
from box2.triage.models import SharepointInvitationQA, Submission

logger = logging.getLogger(__name__)


def make_file_upload_handler(
    docs: DocsClient,
    qa_invitation_list: ListClient,
    submission_list: ListClient,
    download_dir: str = "/tmp/downloads",
) -> Callable[[dict], Awaitable[None]]:
    """Create a handler for newly uploaded files.

    Downloads the file from SharePoint, runs the triage pipeline, maps
    the result to the appropriate SharePoint list schema, and writes it.

    Invitations are written to the QA list for private-office review
    before being forwarded to the minister. Submissions bypass QA and
    go directly to the submissions list.

    Args:
        docs: DocsClient for downloading files from SharePoint.
        qa_invitation_list: ListClient for the QA invitations list.
            Triaged invitations are written here for review.
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
                    fields = to_sharepoint_fields(to_sharepoint_invitation_qa(result))
                    qa_invitation_list.create_item(fields)
                    logger.info(f"Wrote triaged invitation to QA list '{qa_invitation_list.list_name}' for {name}")

                case Submission():
                    fields = to_sharepoint_fields(to_sharepoint_submission(result))
                    submission_list.create_item(fields)
                    logger.info(f"Wrote submission to '{submission_list.list_name}' for {name}")

                case _:
                    logger.info(f"No list write for {name}: result type={type(result).__name__}")
        except Exception as e:
            logger.exception(f"Pipeline failed for file {name} (item_id={item_id}): {type(e).__name__}: {e}")
            raise
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.debug(f"Cleaned up {local_path}")

    return handle_new_file


def make_list_review_handler(
    actions_list: ListClient,
    document_type: Literal["invitation", "submission"],
) -> Callable[[dict], Awaitable[None]]:
    """Create a handler for minister reviews of list items.

    When a minister adds a comment to a submission or invitation in
    SharePoint, this handler extracts actions from the review and
    writes each action as a separate row to the actions list.

    Args:
        actions_list: ListClient for the actions SharePoint list.
        document_type: Whether this handler processes invitation or
            submission reviews.

    Returns:
        An async handler function matching the WebhookRoute signature.
    """

    async def handle_review(item: dict) -> None:
        """Process a minister's review of a list item."""
        item_fields = item.get("fields", {})
        item_id = item.get("id", "unknown")
        minister_comment = item_fields.get("minister_comment")

        if document_type == "invitation":
            minister_decision = item_fields.get("minister_decision")
            if not minister_decision:
                logger.debug(f"Skipping invitation item {item_id}: no minister_decision")
                return
            if minister_decision == "other" and not minister_comment:
                logger.debug(f"Skipping invitation item {item_id}: decision is 'other' but no minister_comment")
                return

        else:
            if not minister_comment:
                logger.debug(f"Skipping submission item {item_id}: no minister_comment")
                return

        logger.info(f"Processing {document_type} review for item {item_id}")

        try:
            review_result = await extract_actions_from_review(item_fields, document_type)

            for action in review_result.actions:
                sp_action = to_sharepoint_action(action, review_result, item_fields, document_type)
                fields = to_sharepoint_fields(sp_action)
                actions_list.create_item(fields)

            logger.info(
                f"Wrote {len(review_result.actions)} action(s) to '{actions_list.list_name}' "
                f"for {document_type} item {item_id}"
            )
        except Exception as e:
            logger.exception(f"Action extraction failed for {document_type} item {item_id}: {type(e).__name__}: {e}")
            raise

    return handle_review


def make_qa_review_handler(
    invitation_list: ListClient,
    rejected_list: ListClient,
    qa_list: ListClient,
) -> Callable[[dict], Awaitable[None]]:
    """Create a handler for private-office QA reviews of invitations.

    When a private-office reviewer sets ``qa_status`` on an item in the
    QA invitations list, this handler routes the item to the appropriate
    destination:

    - **approved** — copied to the minister-facing Invitations list,
      then deleted from the QA list.
    - **rejected** — copied to the Rejected Invitations list (preserving
      QA notes), then deleted from the QA list.
    - **pending** — skipped (reviewer has not finished yet).

    Args:
        invitation_list: ListClient for the minister-facing invitations list.
        rejected_list: ListClient for the rejected invitations list.
        qa_list: ListClient for the QA invitations list (source).

    Returns:
        An async handler function matching the WebhookRoute signature.
    """

    async def handle_qa_review(item: dict) -> None:
        """Route a QA-reviewed invitation to its destination list."""
        item_fields = item.get("fields", {})
        item_id = item.get("id", "unknown")

        qa_item = from_sharepoint_fields(item_fields, SharepointInvitationQA)

        if qa_item.qa_status == "approved":
            logger.info(f"QA approved invitation {item_id}, copying to '{invitation_list.list_name}'")

            try:
                sp_invitation = to_sharepoint_invitation(qa_item)
                fields = to_sharepoint_fields(sp_invitation)
                invitation_list.create_item(fields)
                qa_list.delete_item(item_id)

                logger.info(f"Invitation {item_id} moved to '{invitation_list.list_name}'")
            except Exception as e:
                logger.exception(f"Failed to process approved QA item {item_id}: {type(e).__name__}: {e}")
                raise

        elif qa_item.qa_status == "rejected":
            logger.info(f"QA rejected invitation {item_id}, copying to '{rejected_list.list_name}'")

            try:
                fields = to_sharepoint_fields(qa_item)
                rejected_list.create_item(fields)
                qa_list.delete_item(item_id)

                logger.info(f"Invitation {item_id} moved to '{rejected_list.list_name}'")
            except Exception as e:
                logger.exception(f"Failed to process rejected QA item {item_id}: {type(e).__name__}: {e}")
                raise

        else:
            logger.debug(f"Skipping QA item {item_id}: qa_status='{qa_item.qa_status}' (still pending)")

    return handle_qa_review
