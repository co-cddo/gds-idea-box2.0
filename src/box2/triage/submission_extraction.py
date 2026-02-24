import logging

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from box2.triage.config import model
from box2.triage.exceptions import SubmissionExtractionError
from box2.triage.models import NotSubmission, SafeDocument, Submission

logger = logging.getLogger(__name__)

# System prompt
SUBMISSION_EXTRACTION_INSTRUCTIONS = """
You are an expert at extracting structured information from ministerial submission documents.

Your task is to analyze document text and determine:
1. Is this a ministerial submission requiring a decision? (Submission)
2. Or is this something else? (NotSubmission - e.g., invitation, correspondence, unclear document)

RULES FOR EXTRACTION:
- Only extract information explicitly stated in the document
- Do NOT invent or infer missing details
- If information is unclear or missing, omit it rather than guess
- Extract dates/deadlines as raw text, don't parse or reformat them
- For policy area, identify the primary policy domain from document content

WHAT COUNTS AS A SUBMISSION:
- Documents requesting minister's decision or approval
- Policy recommendations from officials/Deputy Directors
- Documents with phrases like "MINISTERIAL SUBMISSION", "RECOMMENDATION:", "DECISION REQUIRED BY:"
- Documents containing: policy area, official recommendation, responsible Deputy Director signature
- Can be urgent, routine, or for information only

WHAT IS NOT A SUBMISSION:
- Invitations to events (these are handled by a different system)
- General correspondence or thank you notes
- Pure informational updates without recommendations
- Meeting agendas or minutes without decision requests
- Unclear or malformed documents

MINISTERIAL SUBMISSION FORMAT:
Typical submissions include these elements (but not all may be present):
- Title/subject line indicating the policy area
- Policy area or domain (e.g., "AI Safety", "Horizon Europe")
- Background/context section
- Official recommendation from submitting official
- Required decisions or actions from minister
- Responsible Deputy Director name and title
- Decision deadline (if time-sensitive)
- Key dates for implementation
- Related items or precedents
- Urgency assessment (urgent/routine/for_information)

For NotSubmission, provide a brief reason and suggest what category it might be.
For Submission, extract all relevant details accurately.
"""


async def extract_submission(safe_doc: SafeDocument) -> Submission | NotSubmission:
    """
    Extract submission details from document.

    Pure information extraction - doesn't consider minister preferences or make decisions.

    Args:
        safe_doc: Document with PII-redacted text and metadata

    Returns:
        Either a Submission with extracted details or NotSubmission with reason

    Raises:
        SubmissionExtractionError: If extraction fails due to LLM errors, validation errors, or unexpected issues
    """

    agent = Agent(model=model, output_type=Submission | NotSubmission, deps_type=SafeDocument)

    @agent.system_prompt
    def get_system_prompt(ctx):
        doc = ctx.deps

        return f"""{SUBMISSION_EXTRACTION_INSTRUCTIONS}

Here is the document to analyze:

SOURCE: {doc.source_type}
TIMESTAMP: {doc.document_timestamp}

TEXT:
{doc.safe_text}
"""

    logger.info(
        "Extracting submission from document",
        extra={
            "document_title": safe_doc.document_title,
            "document_id": safe_doc.document_id,
            "source_type": safe_doc.source_type,
            "text_length": len(safe_doc.safe_text),
        },
    )

    try:
        result = await agent.run("Extract submission details from this document.", deps=safe_doc)
        output = result.output

        # Log result type
        result_type = type(output).__name__
        logger.info(
            f"Extraction complete: {result_type}",
            extra={"result_type": result_type},
        )

        if isinstance(output, NotSubmission):
            logger.debug(
                f"Not a submission: {output.reason}",
                extra={
                    "reason": output.reason,
                    "suggested_category": output.suggested_category,
                },
            )
        elif isinstance(output, Submission):
            logger.debug(
                f"Submission extracted: {output.policy_area} from {output.responsible_deputy_director}",
                extra={
                    "document_id": output.document_id,
                    "policy_area": output.policy_area,
                    "urgency": output.urgency,
                },
            )

        return output
    except (ModelRetry, UnexpectedModelBehavior) as e:
        logger.error(
            f"LLM failed to extract submission: {str(e)}",
            extra={
                "document_title": safe_doc.document_title,
                "document_id": safe_doc.document_id,
                "text_preview": safe_doc.safe_text[:200],
            },
            exc_info=True,
        )
        raise SubmissionExtractionError(
            f"LLM failed to extract submission from document: {str(e)}",
            text_preview=safe_doc.safe_text[:200] if safe_doc.safe_text else None,
            cause=e,
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected extraction error: {str(e)}",
            extra={
                "document_title": safe_doc.document_title,
                "document_id": safe_doc.document_id,
                "text_preview": safe_doc.safe_text[:200],
            },
            exc_info=True,
        )
        raise SubmissionExtractionError(
            f"Unexpected error during submission extraction: {str(e)}",
            text_preview=safe_doc.safe_text[:200] if safe_doc.safe_text else None,
            cause=e,
        ) from e
