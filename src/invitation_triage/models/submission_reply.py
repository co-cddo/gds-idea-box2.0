"""
Models for submission reply flow.

When Private Office records the minister's response to a submission,
these models capture the freeform response and the formulaic reply.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class SubmissionResponse(BaseModel):
    """Private Office's record of the minister's response to a submission.

    Unlike OfficeResponse (used for invitations), this captures the minister's
    freeform response verbatim without categorising it into yes/no/yes_but.
    """

    submission_id: str = Field(description="Links back to the source Submission")

    minister_response: str = Field(
        min_length=1,
        description="The minister's response verbatim as recorded by Private Office "
        "(e.g., 'Approve but only £2M, not £3M', 'Need more detail on risks', "
        "'Rejected - not a priority right now')",
    )

    responded_at: datetime = Field(
        default_factory=datetime.now,
        description="When this response was recorded",
    )

    responded_by: str = Field(
        default="Private Office",
        description="Who recorded this response (e.g., 'Private Office', staff name)",
    )


class SubmissionReply(BaseModel):
    """Formulaic reply to a ministerial submission.

    Generated deterministically from the submission and minister's response.
    Contains the official recommendation and minister's response verbatim.
    """

    submission_id: str = Field(description="Links back to the source Submission")

    policy_area: str = Field(description="Policy area from the original submission")

    official_recommendation: str = Field(
        description="The official recommendation from the submission, verbatim"
    )

    minister_response: str = Field(
        description="The minister's response, verbatim from SubmissionResponse"
    )

    reply_text: str = Field(
        min_length=20,
        description="Formatted reply text ready to send",
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this reply was generated",
    )
