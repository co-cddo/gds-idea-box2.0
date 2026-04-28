"""Schema for the SharePoint QA invitations list.

Private office reviewers use this list to review, edit, and approve or
reject LLM-extracted invitation data before it reaches the minister.
"""

from typing import Literal

from pydantic import Field

from box2.triage.models.invitation_sharepoint import SharepointInvitation


class SharepointInvitationQA(SharepointInvitation):
    """Data schema for the SharePoint QA Invitations list.

    Extends the minister-facing ``SharepointInvitation`` with fields for
    private-office quality assurance. Items start as ``"pending"`` and are
    moved to the Invitations list on approval or to the Rejected
    Invitations list on rejection.
    """

    qa_status: Literal["pending", "approved", "rejected"] = Field(
        default="pending",
        description="QA review status: pending (awaiting review), approved (forwarded to minister), "
        "or rejected (moved to rejected list)",
    )

    qa_reviewer: str | None = Field(
        default=None,
        description="Name or email of the private office reviewer who assessed this item",
    )

    qa_notes: str | None = Field(
        default=None,
        description="Reviewer notes explaining edits made or reason for rejection",
    )
