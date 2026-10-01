"""SharePoint list schemas.

Pydantic models describing the columns of each SharePoint list this application reads and writes.
They are persistence shapes, not LLM domain objects, so they live with the pipeline mappers that
convert between them and the triage models (``box2.pipeline.mappers``) rather than in ``box2.triage``.
"""

from box2.pipeline.schemas.actions import SharepointAction
from box2.pipeline.schemas.invitation import SharepointInvitation
from box2.pipeline.schemas.invitation_qa import SharepointInvitationQA
from box2.pipeline.schemas.parli_questions import SharepointPQs
from box2.pipeline.schemas.submission import SharepointSubmission

__all__ = [
    "SharepointAction",
    "SharepointInvitation",
    "SharepointInvitationQA",
    "SharepointPQs",
    "SharepointSubmission",
]
