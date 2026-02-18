"""
Test dataset for invitation extraction evaluation.

Current date context: February 4, 2026
All dates are set to be in the near future (February-April 2026) for realistic testing.

EventType values match the schema: meeting, speech, panel, reception, site_visit, conference, other
"""

import pandas as pd

# Define test cases with ground truth
TEST_EMAILS = [
    # ========== CLEAR INVITATIONS ==========
    {
        "email_id": "test_001",
        "subject": "Invitation: Tech Policy Summit 2026",
        "body": """Dear Minister,
        
We cordially invite you to speak at our annual Tech Policy Summit on March 15th, 2026 at the Royal Society.

The event will run from 9:00 AM to 5:00 PM and will bring together 200 policy makers, industry leaders, and academics to discuss AI regulation and digital infrastructure.

We would be honored if you could deliver the keynote address at 10:00 AM.

Please let us know by February 20th if you are able to attend.

Best regards,
Sarah Johnson
Tech Policy Forum""",
        "received_date": "2026-02-01T10:30:00Z",  # 3 days ago
        "has_attachments": True,
        # Ground truth
        "is_invitation": True,
        "expected_event_type": "conference",  # Using enum value
        "expected_host_org": "Tech Policy Forum",
        "expected_date": "2026-03-15",  # 6 weeks away
        "expected_location": "Royal Society",
        "expected_topics": ["AI regulation", "digital infrastructure", "tech policy"],
    },
    {
        "email_id": "test_002",
        "subject": "Speaking Opportunity - Climate Action Week",
        "body": """Minister,

Climate Action Network is hosting a week-long series of events from March 10-14. Would you be available to participate in a panel discussion on government climate commitments?

The panel is scheduled for March 12th at 2 PM at the Conference Centre. You'd be joined by environmental scientists and NGO leaders.

Please confirm by February 25th.

Thanks,
Michael Chen""",
        "received_date": "2026-02-03T14:00:00Z",  # Yesterday
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "panel",  # Using enum value
        "expected_host_org": "Climate Action Network",
        "expected_date": "2026-03-12",  # 5 weeks away
        "expected_location": "Conference Centre",
        "expected_topics": ["climate action", "government commitments", "environment"],
    },
    {
        "email_id": "test_003",
        "subject": "Save the Date: Healthcare Innovation Forum",
        "body": """Dear Minister,

Save the date for our Healthcare Innovation Forum on April 8th. We're still finalizing the venue but wanted to ensure you could keep this date free.

The forum will focus on digital health solutions and NHS modernization. We hope you can join us for a fireside chat.

More details to follow soon.

Dr. Amanda Williams
Healthcare Leaders Association""",
        "received_date": "2026-02-02T09:00:00Z",  # 2 days ago
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "conference",  # Forum is a type of conference
        "expected_host_org": "Healthcare Leaders Association",
        "expected_date": "2026-04-08",  # 9 weeks away
        "expected_location": None,  # Not specified
        "expected_topics": [
            "digital health",
            "NHS modernization",
            "healthcare innovation",
        ],
    },
    # ========== INVITATIONS WITH VAGUE/MISSING DATES ==========
    {
        "email_id": "test_004",
        "subject": "Invitation to Visit Manufacturing Plant",
        "body": """Minister,

British Steel would like to invite you to tour our Sheffield facility sometime in the spring. We'd love to showcase our new sustainable manufacturing processes.

The visit would take approximately 3 hours and include meetings with our workers and management team.

Please let us know your availability in March or April.

Regards,
Robert Davies
British Steel""",
        "received_date": "2026-02-03T11:00:00Z",  # Yesterday
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "site_visit",  # Using enum value
        "expected_host_org": "British Steel",
        "expected_date": None,  # Vague - "spring"
        "expected_location": "Sheffield facility",
        "expected_topics": ["manufacturing", "sustainability", "steel industry"],
    },
    {
        "email_id": "test_005",
        "subject": "Education Roundtable - Late March",
        "body": """Dear Minister,

The Education Policy Institute would like to invite you to a roundtable discussion on education reform late this month or early next month.

We'll be discussing funding models and curriculum changes with headteachers and education experts.

Would you be interested in attending? We can work around your schedule.

Best,
Jennifer Thompson""",
        "received_date": "2026-02-01T10:00:00Z",  # 3 days ago
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "meeting",  # Roundtable is a type of meeting
        "expected_host_org": "Education Policy Institute",
        "expected_date": None,  # Vague - "late March"
        "expected_location": None,
        "expected_topics": ["education reform", "funding models", "curriculum"],
    },
    # ========== INVITATIONS WITH DATE VARIATIONS ==========
    {
        "email_id": "test_006",
        "subject": "Defence Briefing - 18th February",
        "body": """Minister,

We'd like to invite you to a defence briefing on the eighteenth of February at the MOD Main Building.

The briefing will cover recent developments in cybersecurity threats and defence procurement.

Time: 3:00 PM
Duration: 90 minutes

Please RSVP.

General David Clark""",
        "received_date": "2026-02-02T08:00:00Z",  # 2 days ago
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "meeting",  # Briefing is a type of meeting
        "expected_host_org": None,  # Not clearly stated
        "expected_date": "2026-02-18",  # 2 weeks away
        "expected_location": "MOD Main Building",
        "expected_topics": ["defence", "cybersecurity", "procurement"],
    },
    {
        "email_id": "test_007",
        "subject": "Join us next Tuesday",
        "body": """Hi Minister,

Quick invitation - can you join us next Tuesday for a breakfast meeting on housing policy?

We're meeting at the usual place, 8 AM.

Let me know!

Tom""",
        "received_date": "2026-02-03T16:30:00Z",  # Yesterday (Monday)
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "meeting",
        "expected_host_org": None,
        "expected_date": None,  # Relative date "next Tuesday" - would be Feb 11
        "expected_location": None,  # "usual place" is ambiguous
        "expected_topics": ["housing policy"],
    },
    # ========== NOT INVITATIONS - INFORMATIONAL ==========
    {
        "email_id": "test_008",
        "subject": "Monthly Policy Update - January 2026",
        "body": """Dear Minister,

This is our monthly update on policy developments in the transport sector.

Key developments this month:
- New rail franchise agreements signed
- Electric vehicle charging infrastructure expanded by 15%
- Aviation emissions targets published

Full report attached.

For information only - no action required.

Transport Policy Team""",
        "received_date": "2026-02-01T17:00:00Z",  # 3 days ago
        "has_attachments": True,
        "is_invitation": False,
        "expected_reason": "Informational update, no request to attend or participate",
    },
    {
        "email_id": "test_009",
        "subject": "FW: Research Paper - AI Ethics",
        "body": """Minister,

Forwarding this research paper from Oxford University that might be of interest.

They've published new findings on ethical AI governance frameworks.

Thought you'd like to see it.

Best,
Your Private Secretary""",
        "received_date": "2026-02-02T12:00:00Z",  # 2 days ago
        "has_attachments": True,
        "is_invitation": False,
        "expected_reason": "Forwarded document, no specific request or invitation",
    },
    {
        "email_id": "test_010",
        "subject": "Thank You",
        "body": """Dear Minister,

Thank you so much for speaking at our conference last week. Your insights on renewable energy policy were invaluable.

Our members have given overwhelmingly positive feedback. We've attached some photos from the event.

We hope to work with you again in the future.

With gratitude,
Renewable Energy Alliance""",
        "received_date": "2026-02-03T09:30:00Z",  # Yesterday
        "has_attachments": True,
        "is_invitation": False,
        "expected_reason": "Thank you note for past event, not an invitation",
    },
    # ========== NOT INVITATIONS - CONFIRMATIONS ==========
    {
        "email_id": "test_011",
        "subject": "Confirmation: Meeting Tomorrow at 2 PM",
        "body": """Minister,

This is to confirm our meeting tomorrow (Wednesday, February 5th) at 2:00 PM in your office.

Agenda:
- Budget review
- Q2 priorities
- Staffing updates

See you then.

Your Chief of Staff""",
        "received_date": "2026-02-04T09:00:00Z",  # Today (morning)
        "has_attachments": False,
        "is_invitation": False,
        "expected_reason": "Confirmation of already-scheduled meeting, not a new invitation",
    },
    {
        "email_id": "test_012",
        "subject": "Calendar Update: Event Details Confirmed",
        "body": """Dear Minister,

The event you accepted last month has been confirmed:

Date: March 22nd, 2026
Time: 6:00 PM
Venue: Grand Hotel, London
Dress: Black tie

Your speech slot is 7:30 PM. Draft remarks will be sent next week.

No response needed - just a calendar reminder.

Events Team""",
        "received_date": "2026-02-01T10:00:00Z",  # 3 days ago
        "has_attachments": False,
        "is_invitation": False,
        "expected_reason": "Update for already-accepted event, not a new invitation",
    },
    # ========== EDGE CASES - AMBIGUOUS ==========
    {
        "email_id": "test_013",
        "subject": "Coffee Chat?",
        "body": """Hi,

Would love to catch up over coffee sometime to discuss your views on the new trade agreement.

Let me know if you have any time in the next few weeks.

Cheers,
Alex""",
        "received_date": "2026-02-02T14:00:00Z",  # 2 days ago
        "has_attachments": False,
        "is_invitation": True,  # Casual invitation
        "expected_event_type": "meeting",
        "expected_host_org": None,
        "expected_date": None,
        "expected_location": None,
        "expected_topics": ["trade agreement"],
    },
    {
        "email_id": "test_014",
        "subject": "Invitation: Emergency Session on Energy Crisis",
        "body": """URGENT: Minister,

We need to convene an emergency session to discuss the developing energy crisis.

Can you attend a call today at 4 PM? Alternatively tomorrow morning?

This is critical.

Cabinet Office""",
        "received_date": "2026-02-04T13:00:00Z",  # Today at 1 PM
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "meeting",
        "expected_host_org": "Cabinet Office",
        "expected_date": None,  # Multiple options, not specific
        "expected_location": None,  # Call/virtual
        "expected_topics": ["energy crisis"],
    },
    # ========== INVITATIONS WITH MINIMAL INFO ==========
    {
        "email_id": "test_015",
        "subject": "Speaking Request",
        "body": """Dear Minister,

Would you be available to speak at our event?

Please advise.

John Smith
Events Director""",
        "received_date": "2026-02-03T11:00:00Z",  # Yesterday
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "speech",  # Speaking engagement
        "expected_host_org": None,
        "expected_date": None,
        "expected_location": None,
        "expected_topics": [],
    },
    {
        "email_id": "test_016",
        "subject": "Reception Invitation",
        "body": """You are cordially invited to an evening reception.

Date: TBC
Location: TBC

Formal invitation to follow.

Office of the Lord Mayor""",
        "received_date": "2026-02-01T09:00:00Z",  # 3 days ago
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "reception",  # Using enum value
        "expected_host_org": "Office of the Lord Mayor",
        "expected_date": None,
        "expected_location": None,
        "expected_topics": [],
    },
    # ========== NOT INVITATIONS - NEWSLETTERS ==========
    {
        "email_id": "test_017",
        "subject": "Weekly Digest: Economic News",
        "body": """Economic News Roundup - Week of February 3rd

Top Stories:
1. GDP growth exceeds expectations at 2.3%
2. Unemployment drops to 3.8%
3. Inflation remains stable at 2.1%

Expert Commentary:
Leading economists discuss the implications...

Read more at our website.

Subscribe | Unsubscribe | Archive

Economic Policy Institute""",
        "received_date": "2026-02-03T07:00:00Z",  # Yesterday
        "has_attachments": False,
        "is_invitation": False,
        "expected_reason": "Newsletter/digest, no invitation to attend anything",
    },
    {
        "email_id": "test_018",
        "subject": "Announcing Our New Report",
        "body": """Dear Stakeholders,

We are pleased to announce the publication of our annual report on social care reform.

Key findings include:
- 40% increase in home care demand
- Staff shortage remains critical challenge
- Innovation in care technology shows promise

Download the full report: [link]

Social Care Alliance""",
        "received_date": "2026-02-02T10:00:00Z",  # 2 days ago
        "has_attachments": True,
        "is_invitation": False,
        "expected_reason": "Announcement of report publication, not an invitation",
    },
    # ========== COMPLEX INVITATIONS ==========
    {
        "email_id": "test_019",
        "subject": "Multi-Day Trade Mission to Japan",
        "body": """Dear Minister,

The Department for Business and Trade is organizing a trade mission to Japan from April 15-20, 2026.

Itinerary includes:
- Day 1-2: Tokyo (meetings with Japanese government officials)
- Day 3: Osaka (manufacturing site visits)
- Day 4: Kyoto (cultural program)
- Day 5: Tokyo (business roundtable and departure)

This is an excellent opportunity to strengthen UK-Japan trade relations and explore opportunities in technology and advanced manufacturing sectors.

We would need confirmation by March 1st to arrange logistics.

Best regards,
UK Trade Mission Team""",
        "received_date": "2026-02-01T08:00:00Z",  # 3 days ago
        "has_attachments": True,
        "is_invitation": True,
        "expected_event_type": "site_visit",  # Trade mission includes site visits
        "expected_host_org": "Department for Business and Trade",
        "expected_date": "2026-04-15",  # Start date, 10 weeks away
        "expected_location": "Japan (Tokyo, Osaka, Kyoto)",
        "expected_topics": [
            "trade relations",
            "technology",
            "manufacturing",
            "UK-Japan relations",
        ],
    },
    {
        "email_id": "test_020",
        "subject": "Invitation: Annual Charity Gala + Policy Discussion",
        "body": """Minister,

The Children's Education Trust invites you to our annual charity gala on March 28th, 2026 at the Dorchester Hotel.

Evening schedule:
6:30 PM - Reception and drinks
7:30 PM - Dinner
8:30 PM - Keynote address (we hope you'll speak!)
9:00 PM - Auction and entertainment

Additionally, we'd like to arrange a private policy discussion earlier that day (3 PM at our offices) regarding education funding for disadvantaged children.

Please let us know if you can attend either or both events.

Emma Richards
CEO, Children's Education Trust""",
        "received_date": "2026-02-03T12:00:00Z",  # Yesterday
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "reception",  # Primary event is gala/reception
        "expected_host_org": "Children's Education Trust",
        "expected_date": "2026-03-28",  # 7 weeks away
        "expected_location": "Dorchester Hotel",
        "expected_topics": ["education funding", "disadvantaged children", "charity"],
    },
    # ========== MORE EDGE CASES ==========
    {
        "email_id": "test_021",
        "subject": "Question about Your Availability",
        "body": """Dear Minister,

Before we send a formal invitation, could you let us know if you'd generally be available for events in late March?

We're planning a series of regional town halls on local government reform and would love your participation.

No commitment needed yet - just checking general availability.

Local Government Association""",
        "received_date": "2026-02-01T11:00:00Z",  # 3 days ago
        "has_attachments": False,
        "is_invitation": False,  # Pre-invitation inquiry, not actual invitation
        "expected_reason": "Availability inquiry before formal invitation, not an actual invitation yet",
    },
    {
        "email_id": "test_022",
        "subject": "RE: Your Question About Infrastructure",
        "body": """Minister,

Following up on your question from last week's meeting about infrastructure spending projections.

Here is the data you requested:
- 2026: £45 billion
- 2027: £48 billion (projected)
- 2028: £52 billion (projected)

Let me know if you need anything else.

Treasury Team""",
        "received_date": "2026-02-02T14:30:00Z",  # 2 days ago
        "has_attachments": True,
        "is_invitation": False,
        "expected_reason": "Response to minister's previous question, informational only",
    },
    {
        "email_id": "test_023",
        "subject": "Invitation Declined - Thank You",
        "body": """Dear Minister,

Thank you for considering our invitation to speak at the Digital Innovation Summit.

We understand you're unable to attend due to scheduling conflicts. We appreciate you taking the time to respond.

We'll keep you updated on future events.

Best wishes,
Digital Innovation Forum""",
        "received_date": "2026-02-01T16:00:00Z",  # 3 days ago
        "has_attachments": False,
        "is_invitation": False,
        "expected_reason": "Acknowledgment of declined invitation, not a new invitation",
    },
    # ========== INVITATIONS WITH UNUSUAL FORMATS ==========
    {
        "email_id": "test_024",
        "subject": "Re: Re: Re: Fw: Event Next Month",
        "body": """[Previous emails in thread...]

---Original Message---

Hi Minister,

Just circling back on this - can you make the agriculture roundtable on March 6th at the Farmers' Union headquarters?

It's at 10 AM and should run about 2 hours. We'll be discussing subsidy reforms post-Brexit.

Thanks,
Richard""",
        "received_date": "2026-02-02T15:00:00Z",  # 2 days ago
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "meeting",  # Roundtable meeting
        "expected_host_org": "Farmers' Union",
        "expected_date": "2026-03-06",  # 4 weeks away
        "expected_location": "Farmers' Union headquarters",
        "expected_topics": ["agriculture", "subsidy reforms", "Brexit"],
    },
    {
        "email_id": "test_025",
        "subject": "🎤 SPEAKING OPPORTUNITY 🎤 Climate Summit",
        "body": """Hi there! 👋

We would LOVE ❤️ to have you speak at our Climate Summit!!!

📅 Date: March 20th
⏰ Time: 2-4 PM  
📍 Location: Excel London
🎯 Topic: Government climate commitments

Let us know ASAP! 😊

Climate Action Now Team""",
        "received_date": "2026-02-03T09:30:00Z",  # Yesterday
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "speech",  # Speaking at summit
        "expected_host_org": "Climate Action Now Team",
        "expected_date": "2026-03-20",  # 6 weeks away
        "expected_location": "Excel London",
        "expected_topics": ["climate commitments", "climate action"],
    },
    # ========== NOT INVITATIONS - MISCELLANEOUS ==========
    {
        "email_id": "test_026",
        "subject": "Meeting Notes from Yesterday",
        "body": """Minister,

Attached are the notes from yesterday's meeting with the Education Select Committee.

Action items:
- Review draft policy paper (due Friday)
- Schedule follow-up with DfE officials
- Prepare written response to committee questions

Let me know if you have questions.

Your Private Office""",
        "received_date": "2026-02-04T08:00:00Z",  # Today (morning)
        "has_attachments": True,
        "is_invitation": False,
        "expected_reason": "Meeting notes from past event with action items, not an invitation",
    },
    {
        "email_id": "test_027",
        "subject": "Press Enquiry - Request for Comment",
        "body": """Minister,

The Times has requested a comment on the new housing figures released today.

They'd like a response by 5 PM if possible.

Their specific questions:
1. Does the government consider these figures adequate?
2. What additional measures are planned?

Draft response attached for your review.

Press Office""",
        "received_date": "2026-02-04T10:00:00Z",  # Today (morning)
        "has_attachments": True,
        "is_invitation": False,
        "expected_reason": "Press enquiry requesting comment, not an invitation to attend anything",
    },
    # ========== FINAL EDGE CASES ==========
    {
        "email_id": "test_028",
        "subject": "Invitation: Virtual Webinar on Digital Transformation",
        "body": """Dear Minister,

You're invited to join our webinar on digital transformation in public services.

When: Thursday, February 27th at 11:00 AM GMT
Where: Zoom (link to be sent upon registration)
Duration: 60 minutes

We'll be discussing best practices from across Europe and would value your insights.

No preparation required - just join the conversation!

Register here: [link]

Digital Government Network""",
        "received_date": "2026-02-01T10:00:00Z",  # 3 days ago
        "has_attachments": False,
        "is_invitation": True,
        "expected_event_type": "meeting",  # Webinar is a type of meeting
        "expected_host_org": "Digital Government Network",
        "expected_date": "2026-02-27",  # 3 weeks away
        "expected_location": "Virtual/Zoom",
        "expected_topics": ["digital transformation", "public services"],
    },
    {
        "email_id": "test_029",
        "subject": "URGENT: Vote in Parliament Tonight",
        "body": """Minister,

Urgent notification: There will be a division on the Finance Bill tonight at 7 PM.

Your presence is required in the Chamber.

This is a three-line whip.

Chief Whip's Office""",
        "received_date": "2026-02-04T14:00:00Z",  # Today (afternoon)
        "has_attachments": False,
        "is_invitation": False,  # Parliamentary duty notification, not an invitation
        "expected_reason": "Parliamentary whip notification, mandatory duty not an invitation",
    },
    {
        "email_id": "test_030",
        "subject": "Would you be interested in...?",
        "body": """Hi Minister,

I'm reaching out to see if you'd be interested in contributing a foreword to our upcoming report on skills development and workforce training.

The report will be published in Q2 2026 and your perspective would be invaluable.

No pressure - just wanted to gauge your interest.

Best,
Skills Commission""",
        "received_date": "2026-02-03T11:00:00Z",  # Yesterday
        "has_attachments": False,
        "is_invitation": False,  # Request for written contribution, not attendance invitation
        "expected_reason": "Request for written contribution (foreword), not an invitation to attend an event",
    },
]


def create_test_dataframe() -> pd.DataFrame:
    """Create a pandas DataFrame from the test emails."""
    return pd.DataFrame(TEST_EMAILS)


def get_invitations_only() -> pd.DataFrame:
    """Return only emails that should be classified as invitations."""
    df = create_test_dataframe()
    return df[df["is_invitation"] == True].copy()


def get_non_invitations_only() -> pd.DataFrame:
    """Return only emails that should be classified as non-invitations."""
    df = create_test_dataframe()
    return df[df["is_invitation"] == False].copy()


def get_emails_with_dates() -> pd.DataFrame:
    """Return only invitations that have expected dates."""
    df = get_invitations_only()
    return df[df["expected_date"].notna()].copy()


def get_emails_without_dates() -> pd.DataFrame:
    """Return only invitations without expected dates."""
    df = get_invitations_only()
    return df[df["expected_date"].isna()].copy()
