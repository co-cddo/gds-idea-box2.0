import logging
from datetime import datetime

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from box2.triage.calendar import (
    MockCalendar,
    get_calendar_events,
)
from box2.triage.config import model
from box2.triage.exceptions import CalendarError, TriageError
from box2.triage.models import (
    CalendarEvent,
    Invitation,
    MinisterPersona,
    TriagedDecision,
)

logger = logging.getLogger(__name__)


class TriageDeps(BaseModel):
    """Context dependencies passed to the agent at runtime."""

    persona: MinisterPersona
    invite: Invitation


triage_agent = Agent(
    model=model,
    deps_type=TriageDeps,
    output_type=TriagedDecision,
    system_prompt=(
        "You are the Principal Private Secretary (PPS) to a government Minister. "
        "Your role is to triage incoming meeting invitations with political acumen and strategic foresight."
    ),
)


@triage_agent.system_prompt
def inject_persona_and_instructions(ctx: RunContext[TriageDeps]) -> str:
    """
    Dynamically builds the system instructions based on the specific Minister's persona.
    """
    p = ctx.deps.persona
    inv = ctx.deps.invite

    # Format the responsibilities for clear reading
    responsibilities_text = "\n".join(
        [f"- **{dept}**: {', '.join(topics)}" for dept, topics in p.responsibilities.items()]
    )

    # Format the invitation details
    invite_details = f"""
**INVITATION TO TRIAGE:**
- From: {inv.host_org}
- Event Type: {inv.event_type}
- Purpose: {inv.purpose}
- Topics: {", ".join(inv.topics) if inv.topics else "None specified"}
- Proposed Times: {", ".join(inv.proposed_times)}
- Location: {inv.location}
- Time Flexibility: {"Yes - multiple options or flexible timing" if inv.is_time_flexible else "No - specific time required"}
- RSVP Deadline: {inv.deadline_to_respond or "Not specified"}

Summary: {inv.event_summary}
"""

    return f"""
### WHO YOU ARE WORKING FOR

**Minister:** {p.name}
**Role:** {p.role}

**Strategic Priorities (Highest Weight):**
{chr(10).join(f"  {i + 1}. {item}" for i, item in enumerate(p.priorities))}

**Portfolio Responsibilities:**
{responsibilities_text}

**Scheduling Preferences:**
{chr(10).join(f"  - {item}" for item in p.preferences)}

---

{invite_details}

---

### YOUR TRIAGE PROCESS

Follow these steps to make your recommendation:

**STEP 1: Strategic Value Assessment**

Evaluate alignment with the Minister's priorities and responsibilities:
- **HIGH priority** if: Directly advances a Strategic Priority, involves key stakeholders, or unique opportunity
- **MEDIUM priority** if: Relevant to Portfolio Responsibilities, good for relationship building, or sector visibility
- **LOW priority** if: Tangential relevance, routine engagement, or can be delegated

**STEP 2: Calendar Analysis (MANDATORY)**

You MUST check the calendar before making a decision:

1. Parse the proposed times: {", ".join(inv.proposed_times)}
2. For EACH proposed time, call `check_calendar(start_datetime, end_datetime)`
   - If specific time given (e.g., "15th Feb 3-4pm"): check that exact window
   - If flexible (e.g., "anytime Friday"): check the full day/week
3. Assess conflicts:
   - **Hard conflict**: Overlaps with HIGH priority existing commitment
   - **Soft conflict**: Overlaps with MEDIUM/LOW priority event (could be moved)
   - **No conflict**: Time slot is free
4. Consider adjacency: Back-to-back meetings, travel time, preparation needs

**STEP 3: Make Your Decision**

Based on Strategic Value + Calendar Analysis, choose ONE:

- **accept**: High value AND either the time slot is free OR the only conflicts are MEDIUM/LOW
  priority items that the Private Office can reschedule. Accepting implies conflicts will be handled.
- **decline**: Low strategic value, insurmountable schedule conflict with a HIGH priority commitment,
  violates a scheduling preference (e.g. corporate hospitality, overnight travel) without sufficient
  strategic justification, or clearly speculative/low-credibility request.
- **delegate**: Relevant to the portfolio but does NOT directly advance a Strategic Priority. A junior
  minister or PPS could represent the Minister effectively (e.g. networking receptions, opening
  remarks, site tours, routine stakeholder engagement).
- **request_more_info**: The invitation is from a credible organisation AND the topic COULD be relevant,
  but critical details are missing (agenda, attendees, specific objectives) that prevent assessment of
  strategic value. Do NOT use this for clearly low-value or speculative requests — decline those instead.
- **defer**: High value but conflicts with an existing HIGH priority commitment that cannot easily
  be moved. Express interest and propose alternative times.

**STEP 4: Draft the Response**

Write a professional email response (2-4 paragraphs):
- **If accepting**: Confirm attendance, specify chosen time if multiple options, express appropriate enthusiasm
- **If declining**: Gracious thanks, brief reason (without over-explaining), suggest delegation if appropriate
- **If requesting info**: Specific questions needed to make decision
- **If deferring**: Express interest, explain constraint, propose 2-3 alternative dates/times

Tone: Professional, warm but not effusive, ministerial dignity

Sign off: "Office of {p.name}"

---

**IMPORTANT REMINDERS:**
- You MUST call check_calendar for all proposed times before deciding
- Compare event priority vs existing commitments priority
- The Minister's Strategic Priorities trump almost everything else
- Be realistic about prep time, travel, and recovery between events
"""


@triage_agent.tool
async def check_calendar(ctx: RunContext[TriageDeps], start_datetime: str, end_datetime: str) -> list[CalendarEvent]:
    """
    Check the Minister's calendar for events in a time range.

    Use this to check availability for the proposed meeting times.
    You decide the appropriate range based on the invitation's flexibility:
    - Fixed time (e.g., "15th Feb, 3-4pm"):
      check_calendar("2026-02-15 15:00", "2026-02-15 16:00")
    - Flexible day (e.g., "anytime Friday"):
      check_calendar("2026-02-14 00:00", "2026-02-14 23:59")
    - Flexible week (e.g., "week of March 4"):
      check_calendar("2026-03-04 00:00", "2026-03-10 23:59")

    Args:
        start_datetime: Start of range in ISO format 'YYYY-MM-DD HH:MM'
        end_datetime: End of range in ISO format 'YYYY-MM-DD HH:MM'

    Returns:
        List of all calendar events in that range

    Raises:
        CalendarError: If datetime parsing fails or calendar query fails
    """
    logger.debug(f"Calendar check requested: {start_datetime} to {end_datetime}")

    # Parse ISO datetime strings - this is the tool's responsibility
    try:
        start = datetime.fromisoformat(start_datetime.replace(" ", "T"))
        end = datetime.fromisoformat(end_datetime.replace(" ", "T"))
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid datetime format: start='{start_datetime}', end='{end_datetime}'")
        raise CalendarError(
            f"Invalid datetime format. Expected 'YYYY-MM-DD HH:MM', got start='{start_datetime}', end='{end_datetime}'",
            cause=e,
        ) from e

    # Call calendar function - CalendarError will propagate naturally
    events = get_calendar_events(start, end, provider=MockCalendar())
    logger.debug(f"Found {len(events)} events in requested time range")
    return events


async def triage_invitation(invitation: Invitation, persona: MinisterPersona) -> TriagedDecision:
    """
    Triage an invitation with calendar checking.

    Args:
        invitation: The extracted invitation to triage
        persona: Minister's profile and preferences

    Returns:
        TriagedDecision with recommendation and draft response

    Raises:
        TriageError: If triage fails due to LLM errors or unexpected issues
        CalendarError: If calendar checking fails (propagated from tool)
    """
    logger.info(
        f"Triaging invitation from {invitation.host_org}",
        extra={
            "title": invitation.title,
            "email_id": invitation.document_id,
            "host_org": invitation.host_org,
            "event_type": invitation.event_type,
            "minister": persona.name,
        },
    )

    deps = TriageDeps(persona=persona, invite=invitation)

    try:
        result = await triage_agent.run(
            "Please triage this invitation and provide your recommendation.",
            deps=deps,
        )
        decision = result.output

        # Overwrite LLM-generated document_id with the real one
        decision.document_id = invitation.document_id

        logger.info(
            f"Triage complete: {decision.decision} (priority: {decision.priority})",
            extra={
                "title": invitation.title,
                "email_id": invitation.document_id,
                "decision": decision.decision,
                "priority": decision.priority,
            },
        )
        logger.debug(
            f"Reason: {decision.reason}",
            extra={"title": invitation.title, "email_id": invitation.document_id, "reason": decision.reason},
        )

        return decision
    except CalendarError:
        # Re-raise calendar errors as-is (already domain-specific)
        logger.error(
            "Calendar error during triage",
            extra={"email_id": invitation.document_id},
        )
        raise
    except (ModelRetry, UnexpectedModelBehavior) as e:
        logger.error(
            f"LLM failed during triage: {str(e)}",
            extra={"email_id": invitation.document_id},
            exc_info=True,
        )
        raise TriageError(
            f"LLM failed to triage invitation: {str(e)}",
            document_id=invitation.document_id,
            cause=e,
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected triage error: {str(e)}",
            extra={"email_id": invitation.document_id},
            exc_info=True,
        )
        raise TriageError(
            f"Unexpected error during invitation triage: {str(e)}",
            document_id=invitation.document_id,
            cause=e,
        ) from e
