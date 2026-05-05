"""Mappers between pipeline results and SharePoint list schemas.

Provides generic serialisation (``to_sharepoint_fields``) and
deserialisation (``from_sharepoint_fields``) for any Pydantic model
that represents a SharePoint list schema, plus domain-specific mappers
for converting between pipeline result types and SharePoint models.
"""

import re
from datetime import datetime
from typing import Any, Literal, get_origin

from pydantic import BaseModel

from box2.pipeline.models import ActionReviewResult, TriagedInvitation
from box2.sharepoint.graph_api_schema import _contains_url_type, _unwrap_optional
from box2.triage.models import (
    Action,
    SharepointAction,
    SharepointInvitation,
    SharepointInvitationQA,
    SharepointSubmission,
    Submission,
)

# SharePoint internal column names are limited to 32 characters.
# generate_graph_schema sets the internal name from the Pydantic field name,
# but SharePoint silently truncates anything longer.  We must do the same
# when writing items so that field keys match the actual column names.
_SP_INTERNAL_NAME_MAX = 32

# Regex to extract URLs from HTML anchor tags produced by to_sharepoint_fields.
_HREF_PATTERN = re.compile(r'href="([^"]+)"')


# ======================================================================
# Generic serialisation / deserialisation
# ======================================================================


def to_sharepoint_fields(model: BaseModel) -> dict[str, Any]:
    """Serialise a SharePoint Pydantic model to a flat dict for Graph API.

    SharePoint text columns store ``list[str]`` as semicolon-delimited
    strings, and the ``title`` field maps to the built-in ``Title`` column.
    Fields with ``None`` values are omitted entirely (Graph API can 500
    if you send explicit nulls for optional columns).

    URL-typed list fields (e.g. ``list[AnyHttpUrl]``) are formatted as
    HTML anchor tags joined by ``<br>`` so they render as clickable links
    in rich-text SharePoint columns.

    Field names longer than 32 characters are truncated to match
    SharePoint's internal column name limit.

    Args:
        model: Any SharePoint schema model (e.g. SharepointSubmission).

    Returns:
        Dict ready to pass to ``ListClient.create_item()``.
    """
    fields: dict[str, Any] = {}

    # Build a set of field names whose annotations contain URL types,
    # so we can format them as HTML links during serialisation.
    url_fields: set[str] = set()
    for fname, finfo in model.__class__.model_fields.items():
        tp = _unwrap_optional(finfo.annotation)
        if _contains_url_type(tp):
            url_fields.add(fname)

    for name, value in model.model_dump().items():
        # Skip None values — Graph API rejects explicit nulls
        if value is None:
            continue

        # SharePoint's built-in Title column uses capital-T "Title"
        if name == "title":
            key = "Title"
        else:
            key = name[:_SP_INTERNAL_NAME_MAX]

        if isinstance(value, list):
            if name in url_fields:
                links = [f'<a href="{v}">{v}</a>' for v in value if v]
                fields[key] = "<br>".join(links)
            else:
                fields[key] = "; ".join(str(v) for v in value)
        elif isinstance(value, datetime):
            fields[key] = value.isoformat()
        elif isinstance(value, float):
            fields[key] = str(value)
        else:
            fields[key] = value

    return fields


def from_sharepoint_fields[T: BaseModel](fields: dict[str, Any], model_type: type[T]) -> T:
    """Deserialise a SharePoint list item's fields dict into a Pydantic model.

    Inverse of ``to_sharepoint_fields()``. Handles:

    - ``Title`` → ``title`` key mapping.
    - Semicolon-delimited strings → ``list[str]`` fields.
    - HTML anchor tags → ``list[AnyHttpUrl]`` fields.
    - Truncated field name matching (names > 32 chars).
    - Extra keys in *fields* that don't match model fields are ignored.

    Pydantic's ``model_validate`` handles remaining type coercion
    (ISO strings → ``datetime``, strings → ``Literal``/``Enum``, etc.).

    Args:
        fields: Flat dict from a SharePoint list item
            (i.e. ``item["fields"]``).
        model_type: The Pydantic model class to deserialise into.

    Returns:
        A validated instance of *model_type*.
    """
    # Build field classification maps from the model's annotations.
    list_fields: set[str] = set()
    url_fields: set[str] = set()

    for fname, finfo in model_type.model_fields.items():
        tp = _unwrap_optional(finfo.annotation)
        if _contains_url_type(tp):
            url_fields.add(fname)
        elif get_origin(tp) is list:
            list_fields.add(fname)

    # Map SharePoint keys → model field names (handles Title and truncation).
    sp_key_to_field: dict[str, str] = {}
    for fname in model_type.model_fields:
        if fname == "title":
            sp_key_to_field["Title"] = "title"
        else:
            sp_key_to_field[fname[:_SP_INTERNAL_NAME_MAX]] = fname

    # Convert each value back to the type the model expects.
    parsed: dict[str, Any] = {}
    for sp_key, value in fields.items():
        model_key = sp_key_to_field.get(sp_key)
        if model_key is None:
            continue  # Skip SharePoint system fields not on the model

        if model_key in url_fields and isinstance(value, str):
            parsed[model_key] = _extract_urls_from_html(value)
        elif model_key in list_fields and isinstance(value, str):
            parsed[model_key] = _split_list_field(value)
        else:
            parsed[model_key] = value

    return model_type.model_validate(parsed)


def _split_list_field(value: str | list[str] | None) -> list[str]:
    """Split a semicolon-delimited SharePoint text value back to a list.

    SharePoint stores ``list[str]`` fields as ``"; "`` joined strings.
    This helper handles both the serialised string form and the already-
    split list form (e.g. from test fixtures).

    Args:
        value: Semicolon-delimited string, an already-split list, or None.

    Returns:
        List of strings, or an empty list if *value* is falsy.
    """
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [v.strip() for v in value.split(";") if v.strip()]


def _extract_urls_from_html(html: str) -> list[str]:
    """Extract URLs from HTML anchor tags.

    Reverses the HTML link formatting applied by ``to_sharepoint_fields``
    for ``list[AnyHttpUrl]`` fields.

    Args:
        html: HTML string containing ``<a href="...">`` tags joined by
            ``<br>``, or an empty string.

    Returns:
        List of URL strings, or an empty list if no links are found.
    """
    if not html:
        return []
    return _HREF_PATTERN.findall(html)


# ======================================================================
# Domain-specific mappers
# ======================================================================


def to_sharepoint_invitation(qa_item: SharepointInvitationQA) -> SharepointInvitation:
    """Map an approved QA invitation to the minister-facing schema.

    Dynamically copies all fields defined on ``SharepointInvitation`` from
    the QA model, automatically dropping QA-specific fields that only
    exist on the subclass.  This ensures new fields added to
    ``SharepointInvitation`` are picked up without updating this mapper.

    Args:
        qa_item: A ``SharepointInvitationQA`` from the QA list, typically
            constructed via ``from_sharepoint_fields()``.

    Returns:
        SharepointInvitation ready to be serialised via
        ``to_sharepoint_fields()`` and written with ``ListClient.create_item()``.
    """
    shared_fields = {name: getattr(qa_item, name) for name in SharepointInvitation.model_fields}
    return SharepointInvitation(**shared_fields)


def to_sharepoint_invitation_qa(triaged: TriagedInvitation) -> SharepointInvitationQA:
    """Map a triaged invitation to the QA invitations list schema.

    Args:
        triaged: A TriagedInvitation containing extraction and triage results.

    Returns:
        SharepointInvitationQA with ``qa_status`` set to ``"pending"``,
        ready to be serialised via ``to_sharepoint_fields()`` and written
        with ``ListClient.create_item()``.
    """
    inv = triaged.invitation
    dec = triaged.decision

    return SharepointInvitationQA(
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
        urgency=inv.urgency,
        qa_status="pending",
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
        calendar_conflicts=item_fields.get("affected_events") or None,
        summary=review_result.summary,
        minister_comment=minister_comment,
    )
