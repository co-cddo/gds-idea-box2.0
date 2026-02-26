"""Local runner for the file triage pipeline.

Runs triage_file() on a local file, maps the result to the appropriate
SharePoint list schema, and optionally writes it to SharePoint.

Requires AWS credentials for Bedrock (the LLM calls).
Set WRITE_TO_SHAREPOINT = True and provide SharePoint env vars to
write results to a real list.

Usage:
    AWS_PROFILE=aws-prototype uv run python examples/triage/local_pipeline.py <file_path>

Example:
    AWS_PROFILE=aws-prototype uv run python examples/triage/local_pipeline.py examples/data/example_test.txt
    AWS_PROFILE=aws-prototype uv run python examples/triage/local_pipeline.py examples/data/example_invitation.txt

"""

import asyncio
import json
import logging
import sys

from dotenv import load_dotenv

from box2.pipeline import (
    TriagedInvitation,
    to_sharepoint_fields,
    to_sharepoint_invitation,
    to_sharepoint_submission,
    triage_file,
)
from box2.triage.models import NotInvitation, NotSubmission, Submission

load_dotenv()
# ============================================================================
# Configuration
# ============================================================================

WRITE_TO_SHAREPOINT = True

# SharePoint list names (only used when WRITE_TO_SHAREPOINT = True)
INVITATION_LIST_NAME = "Invitations"
SUBMISSION_LIST_NAME = "Submissions"


async def main() -> None:
    """Run the triage pipeline on a file and print / write the result."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if len(sys.argv) < 2:
        print("Usage: uv run python examples/triage/local_pipeline.py <file_path>")
        print("\nExample:")
        print(
            "  AWS_PROFILE=bedrock-dev uv run python examples/triage/local_pipeline.py examples/data/example_test.txt"
        )
        sys.exit(1)

    file_path = sys.argv[1]
    print(f"\nRunning triage pipeline on: {file_path}\n")

    result = await triage_file(file_path)

    # ------------------------------------------------------------------
    # Map result to SharePoint schema and print / write
    # ------------------------------------------------------------------
    match result:
        case TriagedInvitation():
            sp_item = to_sharepoint_invitation(result)
            list_name = INVITATION_LIST_NAME
            print("\n" + "=" * 80)
            print("TRIAGED INVITATION")
            print("=" * 80)

        case Submission():
            sp_item = to_sharepoint_submission(result)
            list_name = SUBMISSION_LIST_NAME
            print("\n" + "=" * 80)
            print("EXTRACTED SUBMISSION")
            print("=" * 80)

        case NotInvitation():
            print("\n" + "=" * 80)
            print(f"NOT AN INVITATION: {result.reason}")
            print("=" * 80)
            return

        case NotSubmission():
            print("\n" + "=" * 80)
            print(f"NOT A SUBMISSION: {result.reason}")
            if result.suggested_category:
                print(f"Suggested category: {result.suggested_category}")
            print("=" * 80)
            return

        case _:
            # DocumentClassification — classified as "other"
            print("\n" + "=" * 80)
            print(f"DOCUMENT TYPE: {result.document_type}")
            print(f"No extraction performed (confidence={result.confidence:.2f})")
            print("=" * 80)
            return

    # Print the SharePoint fields
    fields = to_sharepoint_fields(sp_item)
    print(json.dumps(fields, indent=2, default=str))

    # Optionally write to SharePoint
    if WRITE_TO_SHAREPOINT:
        from box2.sharepoint import ListClient, SharePointSession

        session = SharePointSession.from_env()
        list_client = ListClient(session, list_name=list_name)
        response = list_client.create_item(fields)
        print(f"\nWritten to SharePoint list '{list_name}', item id: {response.get('id')}")
    else:
        print(f"\nDry run — set WRITE_TO_SHAREPOINT = True to write to '{list_name}'")


if __name__ == "__main__":
    asyncio.run(main())
