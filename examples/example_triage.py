"""
End-to-end test of invitation triage.

Usage:
    uv run python examples/example_triage.py
"""

import asyncio
import logging

from box2.triage.models import Invitation, MinisterPersona
from box2.triage.triage import triage_invitation


async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Invitation 1: High-profile AI safety reception
    invitation_1 = Invitation(
        document_id="test_001",
        event_type="reception",
        host_org="UK AI Safety Institute",
        purpose="Launch reception for latest AI safety research findings",
        event_summary="Reception celebrating breakthrough work on AI model evaluation and safety benchmarking. Leading AI researchers and international delegations attending.",
        topics=[
            "ai_and_digital",
            "science_research_ecosystem",
            "international_science",
        ],
        proposed_times=["15th February 2026, 6:00 PM - 8:00 PM"],
        is_time_flexible=False,
        location="The Royal Society, London",
        deadline_to_respond="5th February 2026",
    )

    # Invitation 2: Informal drinks
    invitation_2 = Invitation(
        document_id="test_002",
        event_type="reception",
        host_org="Matt and David",
        purpose="Catch up over drinks",
        event_summary="Informal drinks at Simmons Bar. Matt and David want to catch up.",
        topics=[],
        proposed_times=["Friday evening", "next Tuesday after 6pm"],
        is_time_flexible=True,
        location="Simmons Bar",
        deadline_to_respond=None,
    )

    # Load minister persona
    persona = MinisterPersona.from_json_file("src/box2/triage/data/example_science_minister.json")

    # Test both invitations
    invitations = [invitation_1, invitation_2]

    for i, invitation in enumerate(invitations, 1):
        print("=" * 80)
        print(f"INVITATION {i} OF {len(invitations)}")
        print("=" * 80)

        # Display invitation
        print("\n📧 INVITATION TO TRIAGE:")
        print(f"   Host: {invitation.host_org}")
        print(f"   Event: {invitation.event_type}")
        print(
            f"   Topics: {', '.join(invitation.topics) if invitation.topics else 'None'}"
        )
        print(f"   Time: {', '.join(invitation.proposed_times)}")
        print(f"   Location: {invitation.location}")

        if i == 1:
            print("\n👤 MINISTER:")
            print(f"   {persona.name}")
            print(f"   Top priority: {persona.priorities[0]}")

        # Triage
        print("\n🤖 Triaging (checking calendar & making recommendation)...")

        triaged = await triage_invitation(invitation, persona)

        # Display results
        print("\n📋 DECISION:", triaged.decision.upper())
        print("🎯 PRIORITY:", triaged.priority.upper())

        print("\n💭 REASONING:")
        print(f"   {triaged.reason}")

        if triaged.affected_events:
            print("\n📅 CALENDAR CONFLICTS:")
            for event in triaged.affected_events:
                print(f"   - {event}")
        else:
            print("\n📅 No conflicts")

        print("\n✉️  DRAFT RESPONSE:")
        print("-" * 80)
        print(triaged.draft_response)
        print("-" * 80)
        print()

    print("=" * 80)
    print("✨ All invitations triaged!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
