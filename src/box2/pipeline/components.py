"""Pipeline components for processing classified documents.

Each component handles one document type: extracting structured data and
(for invitations) running the triage decision. These are independently
callable when the caller already has a SafeDocument.
"""

import logging
from pathlib import Path
from typing import Literal

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from box2.pipeline.models import ActionReviewResult, TriagedInvitation
from box2.triage.config import model
from box2.triage.exceptions import ExtractionError
from box2.triage.invitation_extraction import extract_invitation
from box2.triage.models import (
    Invitation,
    MinisterPersona,
    NotInvitation,
    NotSubmission,
    SafeDocument,
    Submission,
)
from box2.triage.submission_extraction import extract_submission
from box2.triage.triage import triage_invitation

logger = logging.getLogger(__name__)

# Resolve the default persona file shipped with the package.
_DEFAULT_PERSONA_PATH = str(
    Path(__file__).resolve().parent.parent / "triage" / "data" / "example_science_minister.json"
)


# ======================================================================
# File triage components
# ======================================================================


async def process_invitation(
    safe_doc: SafeDocument,
    persona: MinisterPersona | None = None,
) -> TriagedInvitation | NotInvitation:
    """Extract an invitation from a document and triage it.

    Runs invitation extraction, then — if a valid invitation is found —
    triages it against the minister's calendar and priorities.

    Args:
        safe_doc: PII-redacted document.
        persona: Minister persona for triage. If ``None``, the default
            example persona shipped with the package is loaded.

    Returns:
        TriagedInvitation if extraction and triage succeeded, or
        NotInvitation if the extractor disagreed with the classifier.

    Raises:
        ExtractionError: If the LLM extraction call fails.
        TriageError: If the LLM triage call fails.
    """
    document_id = safe_doc.document_id

    extraction = await extract_invitation(safe_doc)

    if isinstance(extraction, NotInvitation):
        logger.info(f"Extractor rejected invitation classification for {document_id}: {extraction.reason}")
        return extraction

    invitation: Invitation = extraction
    logger.info(
        f"Invitation extracted for {document_id}: event_type={invitation.event_type}, host={invitation.host_org}"
    )

    # --- Load persona ---
    if persona is None:
        persona = MinisterPersona.from_json_file(_DEFAULT_PERSONA_PATH)
        logger.info(f"Loaded default persona: {persona.name}")

    # --- Triage ---
    decision = await triage_invitation(invitation, persona)

    logger.info(f"Triage complete for {document_id}: decision={decision.decision}, priority={decision.priority}")

    return TriagedInvitation(invitation=invitation, decision=decision)


async def process_submission(
    safe_doc: SafeDocument,
) -> Submission | NotSubmission:
    """Extract a submission from a document.

    Runs submission extraction and returns the result directly.

    Args:
        safe_doc: PII-redacted document.

    Returns:
        Submission if extraction succeeded, or NotSubmission if the
        extractor disagreed with the classifier.

    Raises:
        ExtractionError: If the LLM extraction call fails.
    """
    document_id = safe_doc.document_id

    extraction = await extract_submission(safe_doc)

    if isinstance(extraction, NotSubmission):
        logger.info(f"Extractor rejected submission classification for {document_id}: {extraction.reason}")
        return extraction

    logger.info(
        f"Submission extracted for {document_id}: policy_area={extraction.policy_area}, urgency={extraction.urgency}"
    )

    return extraction


# ======================================================================
# Action extraction from list item reviews
# ======================================================================

INVITATION_DECISION_INSTRUCTIONS = """
You are preparing a single action for Private Office staff based on a minister's decision on an invitation.
The minister's decision is explicit — do NOT infer it from any comment.
YOUR TASK:
Return exactly ONE action of type "correspondence". This single action must capture everything
Private Office needs to know and do.
ACTION FIELDS:
- action_id: short unique identifier, e.g. "ACT-001"
- action_type: always "correspondence"
- description: brief summary of the decision, event details (date, time, location), and any calendar conflicts
- draft_content: a complete, ready-to-send email based on the instructions below
- deadline: the response deadline from the invitation if available
- urgency: based on the response deadline
- owner: "Private Office"
- document_id: "{document_id}"
- source_document_type: "invitation"
- created_at: current timestamp
IF DECISION IS "accept":
- draft_content must be an acceptance email using the existing draft response as the basis
- description must note the event details and any calendar conflicts that need resolving
IF DECISION IS "decline":
- draft_content must be a decline email using the existing draft response as the basis
- description must note the decline and any calendar conflicts that are now freed up
IF DECISION IS "other":
- draft_content must be drafted based on the minister's comment — use it as the direct instruction for what the email should say
- description must clearly explain what Private Office needs to do based on the comment
"""

SUBMISSION_ACTION_REVIEW_INSTRUCTIONS = """
You are extracting actionable items from a minister's review of a {document_type}.

Your task is to:
1. Infer the office decision (yes, yes_but, or no) from the minister's comment.
2. Extract all discrete actions that need to be taken based on the review.
3. Provide a brief summary of the decision and key actions.

DECISION INFERENCE:
- "yes" = the minister approves / accepts as recommended
- "yes_but" = the minister approves with modifications or conditions
- "no" = the minister rejects / declines the recommendation

ACTION EXTRACTION RULES:
- Each action should be a single, discrete task
- Include who should do it (owner) if clear from context
- Include deadlines if mentioned or implied
- For correspondence actions, draft the content if possible
- Set urgency based on deadlines and context
- action_id should be a short unique identifier like "ACT-001", "ACT-002", etc.
- document_id should be set to "{document_id}"
- source_document_type should be "{document_type}"
- created_at should be set to the current timestamp

ACTION TYPES:
- correspondence: Send email/letter/memo
- calendar: Add to minister's calendar
- approval: Sign/approve document
- briefing: Prepare briefing materials
- meeting: Arrange meeting
- notification: Notify stakeholder
- other: Other actions
"""

SUBMISSION_CONTEXT_TEMPLATE = """
DOCUMENT TYPE: Submission

SUBMISSION DETAILS:
- Title: {title}
- Policy Area: {policy_area}
- Official Recommendation: {official_recommendation}
- Required Decisions: {required_decisions}
- Summary: {summary}
- Key Dates: {key_dates}
- Urgency: {urgency}
- Decision Deadline: {decision_deadline}
- Responsible Official: {responsible_deputy_director}

MINISTER'S COMMENT:
{minister_comment}
"""

INVITATION_CONTEXT_TEMPLATE = """
DOCUMENT TYPE: Invitation

INVITATION DETAILS:
- Host: {host_organisation}
- Event Type: {event_type}
- Purpose: {purpose}
- Summary: {event_summary}
- Topics: {topics}
- Proposed Times: {proposed_times}
- Location: {location}
- Calendar Clash: {affected_events}

AI TRIAGE RECOMMENDATION:
- Recommended Decision: {model_decision}
- Priority: {priority}
- Reasoning: {reason}
- Draft Response: {draft_response}

MINISTER'S COMMENT:
{minister_comment}

MINISTER'S DECISION:
{minister_decision}
"""


async def extract_actions_from_review(
    item_fields: dict,
    document_type: Literal["invitation", "submission"],
) -> ActionReviewResult:
    """Extract actions from a minister's review of a SharePoint list item.

    Builds context from the list item fields, calls the LLM to infer
    the office decision and extract discrete actions, and returns a
    structured result.

    Args:
        item_fields: Flat dict of SharePoint list item fields.
        document_type: Whether this is an invitation or submission review.

    Returns:
        ActionReviewResult with inferred decision, actions, and summary.

    Raises:
        ExtractionError: If the LLM call fails.
    """
    document_id = item_fields.get("document_id", "unknown")
    minister_comment = item_fields.get("minister_comment", "")

    logger.info(f"Extracting actions from {document_type} review for {document_id}")

    # Build context string
    if document_type == "submission":
        context = SUBMISSION_CONTEXT_TEMPLATE.format(
            title=item_fields.get("Title", ""),
            policy_area=item_fields.get("policy_area", ""),
            official_recommendation=item_fields.get("official_recommendation", ""),
            required_decisions=item_fields.get("required_decisions", ""),
            summary=item_fields.get("summary", ""),
            key_dates=item_fields.get("key_dates", ""),
            urgency=item_fields.get("urgency", ""),
            decision_deadline=item_fields.get("decision_deadline", ""),
            responsible_deputy_director=item_fields.get("responsible_deputy_director", ""),
            minister_comment=minister_comment,
        )
        instructions = SUBMISSION_ACTION_REVIEW_INSTRUCTIONS.format(
            document_type=document_type,
            document_id=document_id,
        )
    else:
        context = INVITATION_CONTEXT_TEMPLATE.format(
            host_organisation=item_fields.get("host_organisation", ""),
            event_type=item_fields.get("event_type", ""),
            purpose=item_fields.get("purpose", ""),
            event_summary=item_fields.get("event_summary", ""),
            topics=item_fields.get("topics", ""),
            proposed_times=item_fields.get("proposed_times", ""),
            location=item_fields.get("location", ""),
            model_decision=item_fields.get("model_decision", ""),
            priority=item_fields.get("priority", ""),
            reason=item_fields.get("reason", ""),
            draft_response=item_fields.get("draft_response", ""),
            affected_events=item_fields.get("affected_events", ""),
            minister_comment=minister_comment,
            minister_decision=item_fields.get("minister_decision", "not specified"),
        )
        instructions = INVITATION_DECISION_INSTRUCTIONS.format(
            document_id=document_id,
        )

    agent = Agent(
        model=model,
        output_type=ActionReviewResult,
        system_prompt=instructions,
    )

    try:
        result = await agent.run(context)
        output = result.output

        # Ensure all actions have correct document linkage
        for action in output.actions:
            action.document_id = document_id
            action.source_document_type = document_type

        logger.info(
            f"Action extraction complete for {document_id}: "
            f"decision={output.office_decision}, actions={len(output.actions)}"
        )

        return output
    except (ModelRetry, UnexpectedModelBehavior) as e:
        logger.error(f"LLM failed to extract actions for {document_id}: {e}", exc_info=True)
        raise ExtractionError(
            f"LLM failed to extract actions from {document_type} review: {e}",
            document_id=document_id,
            cause=e,
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error extracting actions for {document_id}: {e}", exc_info=True)
        raise ExtractionError(
            f"Unexpected error during action extraction from {document_type} review: {e}",
            document_id=document_id,
            cause=e,
        ) from e
