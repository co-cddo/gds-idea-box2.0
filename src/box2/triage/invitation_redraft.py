"""
LLM-based invitation response redrafting.

When the office responds with 'yes_but' or 'no' to an invitation triage
recommendation, the original draft needs to be modified to reflect the
minister's actual position.

This module handles invitations only. Submissions use deterministic
template formatting via submission_reply.py.
"""

import logging

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from box2.triage.config import model
from box2.triage.exceptions import ExtractionError
from box2.triage.models import TriagedDecision

logger = logging.getLogger(__name__)

REDRAFT_INSTRUCTIONS = """
You are an expert at drafting ministerial correspondence.

Your task is to modify an existing draft invitation response based on new instructions from the minister or Private Office.

RULES FOR REDRAFTING:
- Maintain professional, ministerial tone
- Keep the response concise and clear (1-3 short paragraphs)
- Address the modifications/conditions specified in the office notes
- Preserve the core structure and greeting/closing from original draft where appropriate
- Be specific about changes (dates, amounts, conditions)
- Ensure the redrafted response is ready to send with minimal edits

COMMON REDRAFT SCENARIOS:

1. CONDITIONAL ACCEPTANCE:
   - Original: "I would be delighted to attend..."
   - Notes: "Can only do 7pm onwards, not 6pm"
   - Redraft: Modify to specify the timing constraint while maintaining acceptance

2. DECLINE:
   - Original: "I would be delighted to attend..."
   - Notes: "Cabinet committee conflict, cannot attend"
   - Redraft: Politely decline and explain the conflict

3. DELEGATE:
   - Original: "I would be delighted to attend..."
   - Notes: "Send junior minister instead"
   - Redraft: Express interest, explain delegation, name the delegate

Your redrafted response should be ready to send and accurately reflect the office notes.
"""


async def redraft_invitation_response(
    original_draft: str,
    office_notes: str,
    source: TriagedDecision,
) -> str:
    """
    Redraft an invitation response based on office notes.

    Called when office responds with 'yes_but' or 'no' to modify the original
    system-generated draft for an invitation.

    Args:
        original_draft: The original draft from triage
        office_notes: Office notes explaining modifications/conditions
        source: The original TriagedDecision for context

    Returns:
        Redrafted response text ready to send

    Raises:
        ExtractionError: If redrafting fails
    """

    # Create agent that returns plain string
    agent = Agent(model=model, output_type=str, deps_type=None)

    @agent.system_prompt
    def get_system_prompt(ctx) -> str:
        context = f"""
DOCUMENT TYPE: Invitation
ORIGINAL DECISION: {source.decision}
ORIGINAL REASONING: {source.reason}
"""

        return f"""{REDRAFT_INSTRUCTIONS}

{context}

ORIGINAL DRAFT:
{original_draft}

OFFICE NOTES:
{office_notes}

Redraft the response to incorporate the office notes while maintaining a professional ministerial tone.
Return only the redrafted text, nothing else.
"""

    logger.info(
        "Redrafting invitation response",
        extra={
            "document_id": source.document_id,
            "notes_preview": office_notes[:100],
        },
    )

    try:
        result = await agent.run("Redraft this response based on the office notes.", deps=None)
        redrafted = result.output

        logger.info(
            f"Invitation redraft complete: {len(redrafted)} characters",
            extra={"document_id": source.document_id, "length": len(redrafted)},
        )

        return redrafted

    except (ModelRetry, UnexpectedModelBehavior) as e:
        logger.error(
            f"LLM failed to redraft invitation response: {str(e)}",
            extra={"document_id": source.document_id},
            exc_info=True,
        )
        raise ExtractionError(
            f"LLM failed to redraft invitation response: {str(e)}",
            document_id=source.document_id,
            cause=e,
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error during invitation redraft: {str(e)}",
            extra={"document_id": source.document_id},
            exc_info=True,
        )
        raise ExtractionError(
            f"Unexpected error during invitation redraft: {str(e)}",
            document_id=source.document_id,
            cause=e,
        ) from e
