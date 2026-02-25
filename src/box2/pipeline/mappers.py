"""Mappers from pipeline results to SharePoint list schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from box2.pipeline.models import ActionReviewResult, TriagedInvitation
from box2.triage.models import (
    Action,
    SharepointAction,
    SharepointInvitation,
    SharepointSubmission,
    Submission,
)


def to_sharepoint_fields(model: BaseModel) -> dict[str, Any]:
    """Serialise a SharePoint Pydantic model to a flat dict for Graph API.

    SharePoint text columns store ``list[str]`` as semicolon-delimited
    strings, and the ``title`` field maps to the built-in ``Title`` column.
    Fields with ``None`` values are omitted entirely (Graph API can 500
    if you send explicit nulls for optional columns).

    Args:
        model: Any SharePoint schema model (e.g. SharepointSubmission).

    Returns:
        Dict ready to pass to ``ListClient.create_item()``.
    """
    fields: dict[str, Any] = {}

    for name, value in model.model_dump().items():
        # Skip None values — Graph API rejects explicit nulls
        if value is None:
            continue

        # SharePoint's built-in Title column uses capital-T "Title"
        key = "Title" if name == "title" else name

        if isinstance(value, list):
            fields[key] = "; ".join(str(v) for v in value)
        elif isinstance(value, datetime):
            fields[key] = value.isoformat()
        elif isinstance(value, float):
            fields[key] = str(value)
        else:
            fields[key] = value

    return fields


def to_sharepoint_invitation(triaged: TriagedInvitation) -> SharepointInvitation:
    """Map a triaged invitation to the SharePoint invitation list schema.

    Args:
        triaged: A TriagedInvitation containing extraction and triage results.

    Returns:
        SharepointInvitation ready to be serialised via
        ``to_sharepoint_fields()`` and written with ``ListClient.create_item()``.
    """
    inv = triaged.invitation
    dec = triaged.decision

    return SharepointInvitation(
        title=f"{inv.event_type.value}: {inv.host_org}",
        document_id=inv.document_id,
        event_type=inv.event_type.value,
        host_organisation=inv.host_org,
        purpose=inv.purpose,
        event_summary=inv.event_summary,
        topics=inv.topics,
        proposed_times=inv.proposed_times,
        is_time_flexible=inv.is_time_flexible,
        location=inv.location,
        deadline_to_respond=inv.deadline_to_respond,
        model_decision=dec.decision,
        priority=dec.priority,
        reason=dec.reason,
        draft_response=dec.draft_response,
        affected_events=dec.affected_events,
    )


def to_sharepoint_submission(submission: Submission) -> SharepointSubmission:
    """Map an extracted submission to the SharePoint submission list schema.

    Args:
        submission: A Submission model from the extraction pipeline.

    Returns:
        SharepointSubmission ready to be serialised via
        ``to_sharepoint_fields()`` and written with ``ListClient.create_item()``.
    """
    return SharepointSubmission(
        title=submission.title,
        document_id=submission.document_id,
        policy_area=submission.policy_area,
        responsible_deputy_director=submission.responsible_deputy_director,
        summary=submission.summary,
        submission_date=submission.submission_date.isoformat(),
        decision_deadline=submission.decision_deadline,
        key_dates=submission.key_dates,
        required_decisions=submission.required_decisions,
        official_recommendation=submission.official_recommendation,
        urgency=submission.urgency,
        related_items=submission.related_items,
        overall_confidence=str(submission.overall_confidence) if submission.overall_confidence is not None else None,
    )


def to_sharepoint_action(
    action: Action,
    review_result: ActionReviewResult,
    item_fields: dict,
    document_type: Literal["invitation", "submission"],
) -> SharepointAction:
    """Map a single Action to the SharePoint actions list schema.

    Called once per action in the extraction result. Combines fields from
    the Action, the overall review result, and the source list item.

    Args:
        action: A single extracted action.
        review_result: The full ActionReviewResult (for office_decision and summary).
        item_fields: The source SharePoint list item fields.
        document_type: Whether this came from an invitation or submission review.

    Returns:
        SharepointAction ready to be serialised via
        ``to_sharepoint_fields()`` and written with ``ListClient.create_item()``.
    """
    minister_comment = item_fields.get("minister_comment", "")

    return SharepointAction(
        title=action.description[:80] if len(action.description) > 80 else action.description,
        action_id=action.action_id,
        description=action.description,
        action_type=action.action_type,
        draft_content=action.draft_content,
        deadline=action.deadline,
        urgency=action.urgency,
        owner=action.owner,
        status=action.status,
        document_id=action.document_id,
        source_document_type=document_type,
        created_at=action.created_at.isoformat(),
        document_type=document_type,
        office_decision=review_result.office_decision,
        final_draft=minister_comment,
        summary=review_result.summary,
        minister_comment=minister_comment,
    )
