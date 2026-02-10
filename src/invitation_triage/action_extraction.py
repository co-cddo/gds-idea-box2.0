"""
Extract actionable items from office response.

After the office responds to a document (invitation or submission), this module
extracts concrete actions that need to be taken.
"""

import logging

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from invitation_triage.config import model
from invitation_triage.exceptions import ExtractionError
from invitation_triage.models import (
    Action,
    ActionExtractionResult,
    DocumentClassification,
    FinalDraft,
    InvitationResponse,
    SafeDocument,
    Submission,
    SubmissionResponse,
    TriagedDecision,
)

logger = logging.getLogger(__name__)

ACTION_EXTRACTION_INSTRUCTIONS = """
You are an expert at extracting actionable items from ministerial decisions.

Your task is to analyze the office's response to a document and extract concrete actions that need to be taken by Private Office staff.

TYPES OF ACTIONS:

1. **correspondence** - Send email, letter, or memo
   - Should include the final draft text in draft_content
   - Examples: "Send acceptance email to Dr Chen", "Send decision memo to Deputy Director"

2. **calendar** - Add event to minister's calendar
   - Examples: "Add AI Safety Summit to calendar - 15 Feb 2026, 6-8pm"

3. **approval** - Sign or formally approve document
   - Examples: "Sign funding approval", "Approve bilateral agreement"

4. **briefing** - Prepare briefing materials
   - Examples: "Prepare briefing pack on AI safety research"

5. **meeting** - Arrange or schedule meeting
   - Examples: "Arrange bilateral meeting with US counterpart"

6. **notification** - Notify stakeholder of decision
   - Examples: "Notify Treasury of funding decision by 7 Feb"

7. **other** - Any other action type
   - Examples: "Request revised project scope", "Update project tracker"

RULES FOR EXTRACTION:

- Extract ALL necessary actions based on the decision
- Be specific and actionable (who does what by when)
- Include deadlines from the original document
- Set appropriate urgency (urgent/routine/low)
- Suggest appropriate owner (Private Office, specific team, Minister)
- For correspondence actions, include the final draft text
- Only extract actions that actually need to be done (if decision is "no", don't create calendar entries)

COMMON ACTION PATTERNS:

**Invitation - Accept:**
- Correspondence: Send acceptance email (with draft)
- Calendar: Add event to calendar
- Briefing: Prepare briefing materials
- Notification: Confirm RSVP by deadline

**Invitation - Decline:**
- Correspondence: Send decline email (with draft)
- (No calendar or briefing actions)

**Submission - Approve:**
- Correspondence: Send approval memo to official (with draft)
- Approval: Sign approval document
- Notification: Notify relevant stakeholders (Treasury, etc.)

**Submission - Conditional Approve:**
- Correspondence: Send conditional approval with modifications (with draft)
- Notification: Notify stakeholders
- Other: Request revised documents if needed

**Submission - Reject:**
- Correspondence: Send rejection with reasoning (with draft)
- Notification: Notify stakeholders

Extract only the actions that need to be taken. Be practical and specific.
"""


async def extract_actions(
    document: SafeDocument,
    classification: DocumentClassification,
    source: TriagedDecision | Submission,
    office_response: InvitationResponse | SubmissionResponse,
    final_draft: str,
) -> ActionExtractionResult:
    """
    Extract actionable items from office response.

    Args:
        document: The original document
        classification: Document classification
        source: Original TriagedDecision or Submission for context
        office_response: Office's response - InvitationResponse for invitations
            (yes/yes_but/no + notes) or SubmissionResponse for submissions
            (freeform minister response)
        final_draft: Final draft text (original or redrafted)

    Returns:
        ActionExtractionResult with final draft and extracted actions

    Raises:
        ExtractionError: If action extraction fails
    """

    # Prepare context for the agent
    class ActionContext:
        def __init__(self):
            self.document_id = document.document_id
            self.document_type = classification.document_type
            self.final_draft = final_draft

            # Extract office decision/notes based on response type
            if isinstance(office_response, SubmissionResponse):
                self.office_decision = "minister_response"
                self.office_notes = office_response.minister_response
            else:
                self.office_decision = office_response.decision
                self.office_notes = office_response.notes

            # Context from source
            if isinstance(source, TriagedDecision):
                self.original_decision = source.decision
                self.original_reasoning = source.reason
                self.affected_events = source.affected_events
            else:  # Submission
                self.policy_area = source.policy_area
                self.official_recommendation = source.official_recommendation
                self.decision_deadline = source.decision_deadline
                self.required_decisions = source.required_decisions

    context = ActionContext()

    # Create agent
    agent = Agent(
        model=model,
        output_type=list[Action],
        deps_type=ActionContext,
    )

    @agent.system_prompt
    def get_system_prompt(ctx) -> str:
        action_ctx = ctx.deps

        # Build context string
        if action_ctx.document_type == "invitation":
            context_info = f"""
DOCUMENT TYPE: Invitation
ORIGINAL DECISION: {action_ctx.original_decision}
ORIGINAL REASONING: {action_ctx.original_reasoning}
CALENDAR CONFLICTS: {", ".join(action_ctx.affected_events) if action_ctx.affected_events else "None"}
"""
        else:  # Submission
            context_info = f"""
DOCUMENT TYPE: Submission
POLICY AREA: {action_ctx.policy_area}
OFFICIAL RECOMMENDATION: {action_ctx.official_recommendation}
DECISION DEADLINE: {action_ctx.decision_deadline or "Not specified"}
REQUIRED DECISIONS: {", ".join(action_ctx.required_decisions) if action_ctx.required_decisions else "None"}
"""

        return f"""{ACTION_EXTRACTION_INSTRUCTIONS}

{context_info}

OFFICE DECISION: {action_ctx.office_decision}
OFFICE NOTES: {action_ctx.office_notes or "None"}

FINAL DRAFT:
{action_ctx.final_draft}

Extract ALL actionable items from this decision. For correspondence actions, include the final draft in draft_content.
Return a list of Action objects.
"""

    logger.info(
        "Extracting actions",
        extra={
            "document_id": document.document_id,
            "document_type": classification.document_type,
            "office_decision": office_response.decision
            if isinstance(office_response, InvitationResponse)
            else "minister_response",
        },
    )

    try:
        result = await agent.run("Extract all actionable items.", deps=context)
        actions = result.output

        # Build final draft object
        if isinstance(office_response, SubmissionResponse):
            was_modified = True  # Submission replies are always generated from response
            office_notes = office_response.minister_response
        else:
            was_modified = office_response.decision in ["yes_but", "no"]
            office_notes = office_response.notes

        final_draft_obj = FinalDraft(
            document_id=document.document_id,
            content=final_draft,
            was_modified=was_modified,
            office_notes=office_notes,
        )

        # Fill in source document details for each action
        for action in actions:
            action.source_document_id = document.document_id
            action.source_document_type = classification.document_type

        # Generate summary
        action_summary = f"{len(actions)} action(s) extracted"
        if isinstance(office_response, SubmissionResponse):
            decision_text = (
                f"Minister's response: {office_response.minister_response}"
            )
            office_decision_value = "yes"  # Default for ActionExtractionResult
        elif office_response.decision == "yes":
            decision_text = "approved/accepted as recommended"
            office_decision_value = office_response.decision
        elif office_response.decision == "yes_but":
            decision_text = (
                f"approved/accepted with modifications: {office_response.notes}"
            )
            office_decision_value = office_response.decision
        else:  # no
            decision_text = f"declined/rejected: {office_response.notes}"
            office_decision_value = office_response.decision

        summary = f"Decision: {decision_text}. {action_summary}."

        extraction_result = ActionExtractionResult(
            document_id=document.document_id,
            document_type=classification.document_type,
            office_decision=office_decision_value,
            final_draft=final_draft_obj,
            actions=actions,
            summary=summary,
        )

        logger.info(
            f"Action extraction complete: {len(actions)} action(s)",
            extra={
                "document_id": document.document_id,
                "action_count": len(actions),
            },
        )

        return extraction_result

    except (ModelRetry, UnexpectedModelBehavior) as e:
        logger.error(
            f"LLM failed to extract actions: {str(e)}",
            extra={"document_id": document.document_id},
            exc_info=True,
        )
        raise ExtractionError(
            f"LLM failed to extract actions: {str(e)}",
            document_id=document.document_id,
            cause=e,
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error during action extraction: {str(e)}",
            extra={"document_id": document.document_id},
            exc_info=True,
        )
        raise ExtractionError(
            f"Unexpected error during action extraction: {str(e)}",
            document_id=document.document_id,
            cause=e,
        ) from e
