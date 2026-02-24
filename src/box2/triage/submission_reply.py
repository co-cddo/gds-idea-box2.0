"""
Template-based submission reply generation.

When Private Office records the minister's response to a submission,
this module generates a formulaic reply containing the original
recommendation and the minister's response verbatim.

No LLM is used - the output is deterministic string formatting.
"""

import logging

from box2.triage.models import Submission
from box2.triage.models.submission_reply import (
    SubmissionReply,
    SubmissionResponse,
)

logger = logging.getLogger(__name__)

SUBMISSION_REPLY_TEMPLATE = """RE: {policy_area}

Official Recommendation:
{official_recommendation}

Minister's Response:
{minister_response}"""


def generate_submission_reply(
    submission: Submission,
    response: SubmissionResponse,
) -> SubmissionReply:
    """
    Generate a formulaic reply to a ministerial submission.

    Produces a deterministic, template-based reply that includes the original
    recommendation and the minister's response verbatim. No LLM is involved.

    Args:
        submission: The original submission with official recommendation
        response: The minister's freeform response recorded by Private Office

    Returns:
        SubmissionReply with formatted reply_text
    """
    reply_text = SUBMISSION_REPLY_TEMPLATE.format(
        policy_area=submission.policy_area,
        official_recommendation=submission.official_recommendation,
        minister_response=response.minister_response,
    )

    logger.info(
        f"Generated submission reply: {len(reply_text)} characters",
        extra={
            "document_title": submission.document_title,
            "document_id": submission.document_id,
            "policy_area": submission.policy_area,
        },
    )

    return SubmissionReply(
        document_title=submission.document_title,
        document_id=submission.document_id,
        policy_area=submission.policy_area,
        official_recommendation=submission.official_recommendation,
        minister_response=response.minister_response,
        reply_text=reply_text,
    )
