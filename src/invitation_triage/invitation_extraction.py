import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from invitation_triage.config import model
from invitation_triage.exceptions import ExtractionError
from invitation_triage.models import Invitation, NotInvitation, SafeEmail

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


async def extract_invitation(safe_email: SafeEmail) -> Invitation | NotInvitation:
    """
    Extract invitation details from email.

    Pure information extraction - doesn't consider minister preferences.

    Args:
        safe_email: Email with PII redacted

    Returns:
        Either an Invitation with extracted details or NotInvitation with reason

    Raises:
        ExtractionError: If extraction fails due to LLM errors, validation errors, or unexpected issues
    """

    agent = Agent(
        model=model, output_type=Invitation | NotInvitation, deps_type=SafeEmail
    )

    @agent.system_prompt
    def get_system_prompt(ctx: RunContext[SafeEmail]) -> str:
        email = ctx.deps

        return f"""{EXTRACTION_INSTRUCTIONS}

Here is the email to analyze:

SUBJECT: {email.subject}

BODY:
{email.body}

RECEIVED: {email.received_date}
HAS ATTACHMENTS: {email.has_attachments}
"""

    logger.info(
        "Extracting invitation from email",
        extra={"email_id": safe_email.email_id, "subject": safe_email.subject},
    )

    try:
        result = await agent.run(
            "Extract invitation details from this email.", deps=safe_email
        )
        output = result.output

        # Log result type
        result_type = type(output).__name__
        logger.info(
            f"Extraction complete: {result_type}",
            extra={"email_id": safe_email.email_id, "result_type": result_type},
        )

        if isinstance(output, NotInvitation):
            logger.debug(
                f"Not an invitation: {output.reason}",
                extra={"email_id": safe_email.email_id, "reason": output.reason},
            )
        elif isinstance(output, Invitation):
            logger.debug(
                f"Invitation extracted: {output.event_type} from {output.host_org}",
                extra={
                    "email_id": safe_email.email_id,
                    "event_type": output.event_type,
                    "host_org": output.host_org,
                },
            )

        return output
    except (ModelRetry, UnexpectedModelBehavior) as e:
        logger.error(
            f"LLM failed to extract invitation: {str(e)}",
            extra={"email_id": safe_email.email_id},
            exc_info=True,
        )
        raise ExtractionError(
            f"LLM failed to extract invitation from email: {str(e)}",
            email_id=safe_email.email_id,
            cause=e,
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected extraction error: {str(e)}",
            extra={"email_id": safe_email.email_id},
            exc_info=True,
        )
        raise ExtractionError(
            f"Unexpected error during invitation extraction: {str(e)}",
            email_id=safe_email.email_id,
            cause=e,
        ) from e
