"""
Redraft response based on office notes.

When the office responds with 'yes_but' or 'no', the original draft needs to be
modified to reflect the minister's actual position.
"""

import logging

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from invitation_triage.config import model
from invitation_triage.exceptions import ExtractionError
from invitation_triage.models import Submission, TriagedDecision

logger = logging.getLogger(__name__)

REDRAFT_INSTRUCTIONS = """
You are an expert at drafting ministerial correspondence.

Your task is to modify an existing draft response based on new instructions from the minister or Private Office.

RULES FOR REDRAFTING:
- Maintain professional, ministerial tone
- Keep the response concise and clear (1-3 short paragraphs)
- Address the modifications/conditions specified in the office notes
- Preserve the core structure and greeting/closing from original draft where appropriate
- Be specific about changes (dates, amounts, conditions)
- Ensure the redrafted response is ready to send with minimal edits

COMMON REDRAFT SCENARIOS:

1. CONDITIONAL ACCEPTANCE (invitation):
   - Original: "I would be delighted to attend..."
   - Notes: "Can only do 7pm onwards, not 6pm"
   - Redraft: Modify to specify the timing constraint while maintaining acceptance

2. REDUCED APPROVAL (submission):
   - Original: "I approve the £3M funding as recommended..."
   - Notes: "Approve £2M only, not £3M"
   - Redraft: Change amount and add request for revised scope

3. REQUEST MORE INFO (submission):
   - Original: "I approve the funding as recommended..."
   - Notes: "Need more detail on partner commitments first"
   - Redraft: Change to request additional information before deciding

4. DECLINE (invitation):
   - Original: "I would be delighted to attend..."
   - Notes: "Cabinet committee conflict, cannot attend"
   - Redraft: Politely decline and explain the conflict

Your redrafted response should be ready to send and accurately reflect the office notes.
"""


async def redraft_response(
    original_draft: str,
    office_notes: str,
    source: TriagedDecision | Submission,
    document_type: str,
) -> str:
    """
    Redraft response based on office notes.

    Called when office responds with 'yes_but' or 'no' to modify the original
    system-generated draft.

    Args:
        original_draft: The original draft from triage or submission extraction
        office_notes: Office notes explaining modifications/conditions
        source: The original TriagedDecision or Submission for context
        document_type: "invitation" or "submission" for context

    Returns:
        Redrafted response text ready to send

    Raises:
        ExtractionError: If redrafting fails
    """

    # Create agent that returns plain string
    agent = Agent(model=model, output_type=str, deps_type=None)

    @agent.system_prompt
    def get_system_prompt(ctx) -> str:
        # Build context from source
        if isinstance(source, TriagedDecision):
            context = f"""
DOCUMENT TYPE: Invitation
ORIGINAL DECISION: {source.decision}
ORIGINAL REASONING: {source.reason}
"""
        else:  # Submission
            context = f"""
DOCUMENT TYPE: Submission
POLICY AREA: {source.policy_area}
OFFICIAL RECOMMENDATION: {source.official_recommendation}
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
        "Redrafting response",
        extra={
            "document_type": document_type,
            "notes_preview": office_notes[:100],
        },
    )

    try:
        result = await agent.run(
            "Redraft this response based on the office notes.", deps=None
        )
        redrafted = result.output

        logger.info(
            f"Redraft complete: {len(redrafted)} characters",
            extra={"document_type": document_type, "length": len(redrafted)},
        )

        return redrafted

    except (ModelRetry, UnexpectedModelBehavior) as e:
        logger.error(
            f"LLM failed to redraft response: {str(e)}",
            extra={"document_type": document_type},
            exc_info=True,
        )
        raise ExtractionError(
            f"LLM failed to redraft response: {str(e)}",
            text_preview=original_draft[:200],
            cause=e,
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error during redraft: {str(e)}",
            extra={"document_type": document_type},
            exc_info=True,
        )
        raise ExtractionError(
            f"Unexpected error during redraft: {str(e)}",
            text_preview=original_draft[:200],
            cause=e,
        ) from e
