import logging

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from invitation_triage.config import model
from invitation_triage.exceptions import ClassificationError
from invitation_triage.models import SafeUpload, UploadClassification

logger = logging.getLogger(__name__)

# Classification instructions
CLASSIFICATION_INSTRUCTIONS = """
You are an expert at classifying ministerial documents.

Your task is to determine the document type from its text content.

DOCUMENT TYPES:

**invitation** - Requests for minister's attendance/participation at events
- Characteristics: Event-focused, has date/time/location, requests attendance
- Examples: Conference invitations, reception invites, speaking requests, panel participation
- Key indicators: "invite you", "please join us", event dates, venue information, RSVP requests
- Focus: Asks minister to physically or virtually attend something

**submission** - Ministerial submissions requesting decisions/approvals
- Characteristics: Policy-focused, has recommendations from officials, requests decision
- Examples: Policy recommendations, funding requests, quarterly reviews, briefings requiring action
- Key indicators: "MINISTERIAL SUBMISSION", "RECOMMENDATION:", official signatures (Deputy Director), decision deadlines
- Focus: Asks minister to approve, reject, or note policy matters

**other** - Everything else
- General correspondence, thank you notes, FYI emails, unclear documents
- Use this when document doesn't clearly fit invitation or submission
- Examples: Thank you letters, general updates, forwarded documents without clear ask

RULES:
- Base classification ONLY on the text content provided
- Be confident in clear cases (confidence 0.9+)
- Use lower confidence (0.5-0.7) if ambiguous or features of multiple types
- Provide clear reasoning for your choice
- When in doubt between invitation and submission, check: does it ask for attendance (invitation) or a decision (submission)?
"""


async def classify_upload(safe_upload: SafeUpload) -> UploadClassification:
    """
    Classify document type from safe upload.

    Simple agent with no tools - pure classification based on text and metadata.

    Args:
        safe_upload: Document with PII-redacted text and metadata

    Returns:
        UploadClassification with type, confidence, and reasoning

    Raises:
        ClassificationError: If classification fails due to LLM errors or unexpected issues
    """

    agent = Agent(
        model=model,
        output_type=UploadClassification,
        deps_type=SafeUpload,
    )

    @agent.system_prompt
    def get_system_prompt(ctx):
        doc = ctx.deps

        # Include metadata context if available
        metadata_str = ""
        if doc.source_type:
            metadata_str += f"\nSOURCE: {doc.source_type}"
        if doc.filename:
            metadata_str += f"\nFILENAME: {doc.filename}"

        return f"""{CLASSIFICATION_INSTRUCTIONS}

Here is the document to classify:
{metadata_str}

TEXT:
{doc.safe_text}
"""

    logger.info(
        "Classifying document",
        extra={
            "upload_id": safe_upload.upload_id,
            "text_length": len(safe_upload.safe_text),
            "source_type": safe_upload.source_type,
        },
    )

    try:
        result = await agent.run("Classify this document type.", deps=safe_upload)
        classification = result.output

        logger.info(
            f"Classification complete: {classification.document_type} (confidence: {classification.confidence:.2f})",
            extra={
                "upload_id": safe_upload.upload_id,
                "document_type": classification.document_type,
                "confidence": classification.confidence,
            },
        )

        return classification

    except (ModelRetry, UnexpectedModelBehavior) as e:
        logger.error(
            f"LLM failed to classify document: {str(e)}",
            extra={"upload_id": safe_upload.upload_id},
            exc_info=True,
        )
        raise ClassificationError(
            f"LLM failed to classify document: {str(e)}",
            text_preview=safe_upload.safe_text[:200],
            cause=e,
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected classification error: {str(e)}",
            extra={"upload_id": safe_upload.upload_id},
            exc_info=True,
        )
        raise ClassificationError(
            f"Unexpected error during classification: {str(e)}",
            text_preview=safe_upload.safe_text[:200],
            cause=e,
        ) from e
