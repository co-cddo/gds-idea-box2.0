"""Local test for action extraction from a simulated minister review.

Builds fake SharePoint list item fields (as if a submission had been
written to the list and the minister added a comment), then runs
extract_actions_from_review() and optionally writes the resulting
actions to an Actions SharePoint list.

Usage:
    AWS_PROFILE=bedrock-dev uv run python examples/triage/local_action_extraction.py

"""

import asyncio
import json
import logging

from dotenv import load_dotenv

from box2.pipeline import (
    extract_actions_from_review,
    to_sharepoint_action,
    to_sharepoint_fields,
)

load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

WRITE_TO_SHAREPOINT = True
ACTIONS_LIST_NAME = "Actions_Tracker"

# ============================================================================
# Simulated SharePoint list item fields
# ============================================================================

# These mimic what a submission list item looks like after the minister
# has reviewed it and added a comment in SharePoint.

FAKE_SUBMISSION_ITEM = {
    "Title": "AI Safety Summit Attendance and Funding Allocation",
    "document_id": "file_64d9ef5757a5f7cf",
    "policy_area": "AI Safety and International Collaboration",
    "responsible_deputy_director": "Dr. Sarah Chen, Deputy Director - AI Policy",
    "summary": (
        "This submission requests ministerial approval for UK participation "
        "in the upcoming AI Safety Summit, including a proposed £3M funding "
        "allocation from the contingency reserve to support preparation and "
        "delegation costs."
    ),
    "submission_date": "2026-02-25T14:42:48",
    "decision_deadline": "7 February 2026 (Treasury deadline for contingency draw-down)",
    "key_dates": "10 Feb: International announcement; 15 Feb: Contracts must be signed",
    "required_decisions": "Approve £3M from contingency reserve; Confirm UK delegation lead",
    "official_recommendation": "Approve £3M from contingency reserve and confirm ministerial attendance",
    "urgency": "urgent",
    "related_items": "Previous contingency draw-down for quantum centre (Oct 2025)",
    "overall_confidence": "0.85",
    "minister_comment": (
        "Approve but only £2M not £3M. I want Sarah Chen to lead the delegation. "
        "Make sure we have a strong position paper on frontier model evaluation "
        "ready before the summit. Also arrange a briefing with the Chief Scientific "
        "Adviser before I travel."
    ),
}

FAKE_INVITATION_ITEM = {
    "Title": "conference: The Royal Society",
    "document_id": "file_abc123def456",
    "event_type": "conference",
    "host_organisation": "The Royal Society",
    "purpose": "Deliver keynote address at the International AI Governance Forum",
    "event_summary": (
        "Two-day forum bringing together policymakers, researchers and industry "
        "leaders from 30+ countries to discuss AI safety regulation."
    ),
    "topics": "frontier model evaluation; international regulatory alignment; responsible AI",
    "proposed_times": "Morning of 20 March 2026; Afternoon of 21 March 2026",
    "is_time_flexible": "true",
    "location": "The Royal Society, London",
    "deadline_to_respond": "28 February 2026",
    "model_decision": "accept",
    "priority": "high",
    "reason": "Directly aligns with minister's AI safety priorities and provides international visibility",
    "draft_response": (
        "Thank you for the invitation. The Minister is pleased to accept and will deliver the keynote on 20 March."
    ),
    "affected_events": "",
    "minister_comment": (
        "Yes accept but I can only do the morning of the 20th. "
        "Make sure my speech covers our new frontier model evaluation framework. "
        "I'd like a prep briefing the week before."
    ),
    "minister_decision": "yes_but",
}


async def main() -> None:
    """Run action extraction on simulated list items."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ------------------------------------------------------------------
    # Test 1: Submission review
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("TEST 1: SUBMISSION REVIEW")
    print("=" * 80)
    print(f"\nMinister's comment: {FAKE_SUBMISSION_ITEM['minister_comment']}\n")

    submission_result = await extract_actions_from_review(FAKE_SUBMISSION_ITEM, "submission")

    print(f"\nInferred office decision: {submission_result.office_decision}")
    print(f"Summary: {submission_result.summary}")
    print(f"Actions extracted: {len(submission_result.actions)}")

    for i, action in enumerate(submission_result.actions, 1):
        sp_action = to_sharepoint_action(action, submission_result, FAKE_SUBMISSION_ITEM, "submission")
        fields = to_sharepoint_fields(sp_action)
        print(f"\n--- Action {i} ---")
        print(json.dumps(fields, indent=2, default=str))

    # ------------------------------------------------------------------
    # Test 2: Invitation review
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("TEST 2: INVITATION REVIEW")
    print("=" * 80)
    print(f"\nMinister's comment: {FAKE_INVITATION_ITEM['minister_comment']}\n")

    invitation_result = await extract_actions_from_review(FAKE_INVITATION_ITEM, "invitation")

    print(f"\nInferred office decision: {invitation_result.office_decision}")
    print(f"Summary: {invitation_result.summary}")
    print(f"Actions extracted: {len(invitation_result.actions)}")

    for i, action in enumerate(invitation_result.actions, 1):
        sp_action = to_sharepoint_action(action, invitation_result, FAKE_INVITATION_ITEM, "invitation")
        fields = to_sharepoint_fields(sp_action)
        print(f"\n--- Action {i} ---")
        print(json.dumps(fields, indent=2, default=str))

    # ------------------------------------------------------------------
    # Optionally write to SharePoint
    # ------------------------------------------------------------------
    if WRITE_TO_SHAREPOINT:
        from box2.sharepoint import ListClient, SharePointSession

        session = SharePointSession.from_env()
        actions_list = ListClient(session, list_name=ACTIONS_LIST_NAME)

        all_actions = []
        for action in submission_result.actions:
            all_actions.append(to_sharepoint_action(action, submission_result, FAKE_SUBMISSION_ITEM, "submission"))
        for action in invitation_result.actions:
            all_actions.append(to_sharepoint_action(action, invitation_result, FAKE_INVITATION_ITEM, "invitation"))

        for sp_action in all_actions:
            fields = to_sharepoint_fields(sp_action)
            response = actions_list.create_item(fields)
            print(f"\nWritten action '{sp_action.title[:50]}...' to '{ACTIONS_LIST_NAME}', id: {response.get('id')}")
    else:
        print(f"\nDry run — set WRITE_TO_SHAREPOINT = True to write to '{ACTIONS_LIST_NAME}'")


if __name__ == "__main__":
    asyncio.run(main())
