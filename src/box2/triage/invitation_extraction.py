import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from box2.triage.config import model
from box2.triage.exceptions import ExtractionError
from box2.triage.models import Invitation, NotInvitation, SafeDocument

logger = logging.getLogger(__name__)

# System prompt
EXTRACTION_INSTRUCTIONS = """
You are an expert at extracting structured information from ministerial invitation emails.

Your task is to analyze an email and determine:
1. Is this an invitation requiring a response? (Invitation)
2. Or is this something else? (NotInvitation - e.g., informational update, thank you note, forwarded document)

RULES FOR EXTRACTION:
- Only extract information explicitly stated in the email
- Use your best judgment for categorization (event type, topics)
- Do NOT invent or infer missing details
- If information is unclear or missing, omit it rather than guess
- For topics, identify relevant policy areas based on the email content

WHAT COUNTS AS AN INVITATION:
- Requests for attendance at events, meetings, receptions, speeches
- Requests for participation in panels, conferences, site visits
- "Save the date" notices with clear asks to attend
- Invitations with or without confirmed dates

WHAT IS NOT AN INVITATION:
- Pure informational updates or newsletters
- Thank you notes or acknowledgments
- Forwarded documents without a specific ask
- Meeting confirmations for already-accepted events
- General correspondence

For NotInvitation, provide a brief reason explaining why it's not an invitation.
For Invitation, extract all relevant details accurately.
"""


async def extract_invitation(safe_doc: SafeDocument) -> Invitation | NotInvitation:
    """
    Extract invitation details from document.

    Pure information extraction - doesn't consider minister preferences.

    Args:
        safe_doc: Document with PII-redacted text and metadata

    Returns:
        Either an Invitation with extracted details or NotInvitation with reason

    Raises:
        ExtractionError: If extraction fails due to LLM errors, validation errors, or unexpected issues
    """

    agent = Agent(
        model=model, output_type=Invitation | NotInvitation, deps_type=SafeDocument
    )

    @agent.system_prompt
    def get_system_prompt(ctx: RunContext[SafeDocument]) -> str:
        doc = ctx.deps

        return f"""{EXTRACTION_INSTRUCTIONS}

Here is the document to analyze:

SOURCE: {doc.source_type}
TIMESTAMP: {doc.document_timestamp}

TEXT:
{doc.safe_text}
"""

    logger.info(
        "Extracting invitation from document",
        extra={
            "document_id": safe_doc.document_id,
            "source_type": safe_doc.source_type,
        },
    )

    try:
        result = await agent.run(
            "Extract invitation details from this document.", deps=safe_doc
        )
        output = result.output

        # Log result type
        result_type = type(output).__name__
        logger.info(
            f"Extraction complete: {result_type}",
            extra={"document_id": safe_doc.document_id, "result_type": result_type},
        )

        if isinstance(output, NotInvitation):
            logger.debug(
                f"Not an invitation: {output.reason}",
                extra={"document_id": safe_doc.document_id, "reason": output.reason},
            )
        elif isinstance(output, Invitation):
            logger.debug(
                f"Invitation extracted: {output.event_type} from {output.host_org}",
                extra={
                    "document_id": safe_doc.document_id,
                    "event_type": output.event_type,
                    "host_org": output.host_org,
                },
            )

        return output
    except (ModelRetry, UnexpectedModelBehavior) as e:
        logger.error(
            f"LLM failed to extract invitation: {str(e)}",
            extra={"document_id": safe_doc.document_id},
            exc_info=True,
        )
        raise ExtractionError(
            f"LLM failed to extract invitation from document: {str(e)}",
            document_id=safe_doc.document_id,
            cause=e,
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected extraction error: {str(e)}",
            extra={"document_id": safe_doc.document_id},
            exc_info=True,
        )
        raise ExtractionError(
            f"Unexpected error during invitation extraction: {str(e)}",
            document_id=safe_doc.document_id,
            cause=e,
        ) from e
