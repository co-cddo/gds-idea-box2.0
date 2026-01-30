from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from invitation_triage.config import model
from invitation_triage.exceptions import ExtractionError
from invitation_triage.models import Invitation, NotInvitation, SafeEmail

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

    try:
        result = await agent.run(
            "Extract invitation details from this email.", deps=safe_email
        )
        return result.output
    except (ModelRetry, UnexpectedModelBehavior) as e:
        raise ExtractionError(
            f"LLM failed to extract invitation from email: {str(e)}",
            email_id=safe_email.email_id,
            cause=e,
        ) from e
    except Exception as e:
        raise ExtractionError(
            f"Unexpected error during invitation extraction: {str(e)}",
            email_id=safe_email.email_id,
            cause=e,
        ) from e
