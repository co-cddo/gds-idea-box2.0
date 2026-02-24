"""
Test dataset for triage evaluation against the MockCalendar schedule.

These test cases use the actual minister persona and reflect realistic conflict
assessment based on the triage prompt's logic: strategic value vs calendar priority.
"""

from box2.triage.models import (
    EventType,
    Invitation,
)

# Actual Minister Persona
TEST_PERSONA = {
    "name": "Minister for Science, Innovation and Technology",
    "role": "Parliamentary Under-Secretary of State",
    "priorities": [
        "AI safety and governance",
        "Quantum technology commercialization",
        "Science and research investment",
        "Nuclear innovation and deployment",
        "University research ecosystem strengthening",
    ],
    "responsibilities": {
        "dsit": [
            "ai_and_digital",
            "quantum_technologies",
            "engineering_biology",
            "life_sciences",
            "research_and_development",
            "science_research_ecosystem",
            "international_science",
            "horizon_europe",
            "tech_innovation",
            "universities_talent",
            "oxford_cambridge_corridor",
        ],
        "desnz": [
            "nuclear_energy",
            "fusion_technology",
            "climate_innovation",
            "energy_innovation",
            "ai_in_energy",
        ],
        "cross_cutting": [
            "public_engagement",
            "international_partnerships",
            "industry_collaboration",
            "skills_workforce",
            "regional_development",
        ],
    },
    "preferences": [
        "No corporate hospitality or gifts",
        "Prefer meetings Monday to Wednesday",
        "Avoid events requiring overnight travel unless strategically critical",
        "Prioritize events with international delegations or key stakeholders",
        "Prefer morning meetings over evening receptions",
        "Limit Friday commitments for constituency work",
    ],
}

TRIAGE_TEST_CASES = [
    # ========== CASE 1: TOP PRIORITY AI BUT conflicts with Horizon Europe - ACCEPT, need to move Horizon Europe ==========
    {
        "test_id": "triage_001",
        "description": "AI Safety Summit - conflicting high priority with strategic priority but justified deferral",
        "invitation": Invitation(
            document_id="inv_001",
            event_type=EventType.MEETING,
            host_org="UK AI Safety Institute",
            purpose="Emergency briefing on AI safety governance framework",
            event_summary="Urgent briefing with AI Safety Institute leadership on critical updates to UK's AI safety framework. International delegations arriving for key discussions. Minister's input needed before formal announcement.",
            topics=["AI safety", "governance", "international"],
            proposed_times=["Monday, February 9th, 2026, 8:30 AM - 9:30 AM"],
            is_time_flexible=True,
            location="Department for Science, Innovation and Technology",
        ),
        "expected": {
            "decision": "defer",
            "priority": "high",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "AI safety top priority",
                "international delegations",
                "worth rescheduling PO briefing",
                "urgent timeline",
            ],
        },
    },
    # ========== CASE 2: Medium Priority vs High Priority - DEFER ==========
    {
        "test_id": "triage_002",
        "description": "University research meeting conflicts with high-priority internal session",
        "invitation": Invitation(
            document_id="inv_002",
            event_type=EventType.MEETING,
            host_org="Russell Group Universities",
            purpose="Discussion on university research funding challenges",
            event_summary="Vice-Chancellors from 8 research-intensive universities want to discuss research funding pressures, infrastructure needs, and talent retention concerns.",
            topics=["universities", "research funding", "talent"],
            proposed_times=["Monday, February 2nd, 2026, 9:15 AM - 10:15 AM"],
            is_time_flexible=True,
            location="Russell Group Offices, London",
        ),
        "expected": {
            "decision": "defer",
            "priority": "high",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "university research ecosystem priority",
                "conflicts with Horizon Europe briefing",
                "propose afternoon slot",
                "1:00 PM - 2:00 PM available",
            ],
        },
    },
    # ========== CASE 3: Perfect Fit, Portfolio Responsibility - ACCEPT ==========
    {
        "test_id": "triage_003",
        "description": "Quantum technology meeting fits perfectly in available Thursday slot",
        "invitation": Invitation(
            document_id="inv_003",
            event_type=EventType.MEETING,
            host_org="UK Quantum Technology Hub Network",
            purpose="Quarterly progress review on quantum commercialization",
            event_summary="Hub directors presenting progress on quantum commercialization pathways, industry partnerships, and technology transfer. Directly relevant to quantum technology commercialization priority.",
            topics=["quantum technologies", "commercialization", "industry"],
            proposed_times=["Thursday, February 5th, 2026, 11:00 AM - 12:00 PM"],
            is_time_flexible=True,
            location="Virtual",
        ),
        "expected": {
            "decision": "accept",
            "priority": "high",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "quantum technology commercialization top priority",
                "fits perfectly between morning and afternoon",
                "11 AM slot available",
                "no conflicts",
            ],
        },
    },
    # ========== CASE 4: Evening Reception - Against Preference - DELEGATE ==========
    {
        "test_id": "triage_004",
        "description": "Evening reception violates morning preference - delegate",
        "invitation": Invitation(
            document_id="inv_004",
            event_type=EventType.RECEPTION,
            host_org="TechUK",
            purpose="Evening networking reception for digital innovation",
            event_summary="200+ attendees from tech sector. Evening drinks and networking. Minister invited to give brief opening remarks.",
            topics=["tech innovation", "industry networking"],
            proposed_times=["Tuesday, February 3rd, 2026, 6:00 PM - 8:00 PM"],
            is_time_flexible=False,
            location="The Shard, London",
        ),
        "expected": {
            "decision": "delegate",
            "priority": "low",
            "should_mention_calendar": False,
            "key_reasoning_points": [
                "evening reception",
                "prefer morning meetings",
                "suitable for junior minister",
                "networking rather than strategic",
            ],
        },
    },
    # ========== CASE 5: High Priority Quantum - Worth Moving Medium Conflict with Horizon Comms planning - ACCEPT ==========
    {
        "test_id": "triage_005",
        "description": "Quantum breakthrough briefing - worth rescheduling comms meeting",
        "invitation": Invitation(
            document_id="inv_005",
            event_type=EventType.MEETING,
            host_org="National Quantum Computing Centre",
            purpose="Briefing on quantum error correction breakthrough",
            event_summary="Researchers achieved major advance in quantum error correction - want to brief Minister before public announcement. Significant implications for UK quantum commercialization timeline and international competitiveness.",
            topics=["quantum computing", "research breakthrough", "commercialization"],
            proposed_times=["Thursday, February 5th, 2026, 10:15 AM - 11:00 AM"],
            is_time_flexible=True,
            location="Virtual",
        ),
        "expected": {
            "decision": "accept",
            "priority": "high",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "quantum technology top priority",
                "breakthrough announcement time-sensitive",
                "Horizon comms can be rescheduled",
                "worth moving medium-priority conflict",
            ],
        },
    },
    # ========== CASE 6: Nuclear Energy - Strategic Fit but conflicts with medium and high priority meeting - DEFER ==========
    {
        "test_id": "triage_006",
        "description": "Nuclear innovation roundtable fits Friday morning perfectly",
        "invitation": Invitation(
            document_id="inv_006",
            event_type=EventType.MEETING,
            host_org="UK Nuclear Innovation Group",
            purpose="Small modular reactor deployment discussion",
            event_summary="Industry leaders and national labs discussing SMR deployment pathways, regulatory framework, and investment landscape. Key stakeholders for nuclear innovation priority.",
            topics=["nuclear energy", "innovation", "SMR", "deployment"],
            proposed_times=["Friday, February 6th, 2026, 9:30 AM - 10:30 AM"],
            is_time_flexible=True,
            location="Virtual",
        ),
        "expected": {
            "decision": "defer",
            "priority": "high",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "nuclear innovation top priority",
                "conflicts with GOTT and Life sciences meeting",
                "suggest 11:00 AM slot",
                "Friday morning acceptable",
            ],
        },
    },
    # ========== CASE 7: Friday Afternoon - Against Preference - DECLINE ==========
    {
        "test_id": "triage_007",
        "description": "Friday afternoon panel violates constituency work preference",
        "invitation": Invitation(
            document_id="inv_007",
            event_type=EventType.PANEL,
            host_org="Science Communication Forum",
            purpose="Panel on public engagement with science",
            event_summary="Discussion panel on effective science communication strategies with academics and media professionals.",
            topics=["public engagement", "science communication"],
            proposed_times=["Friday, February 6th, 2026, 3:00 PM - 4:30 PM"],
            is_time_flexible=False,
            location="London",
        ),
        "expected": {
            "decision": "decline",
            "priority": "low",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "Friday afternoon",
                "constituency work commitments",
                "scheduling preference",
                "medium strategic value",
            ],
        },
    },
    # ========== CASE 8: Multiple Time Options - One Works - ACCEPT ==========
    {
        "test_id": "triage_008",
        "description": "AI governance roundtable with multiple times - Monday afternoon works",
        "invitation": Invitation(
            document_id="inv_008",
            event_type=EventType.MEETING,
            host_org="Alan Turing Institute",
            purpose="AI governance framework expert roundtable",
            event_summary="Leading AI researchers and ethicists discussing governance frameworks for frontier AI systems. Key stakeholder input for AI safety priority. International experts attending.",
            topics=["AI safety", "governance", "research", "international"],
            proposed_times=[
                "Monday, February 2nd, 2026, 11:30 AM - 12:30 PM",
                "Monday, February 2nd, 2026, 1:30 PM - 2:30 PM",
                "Tuesday, February 3rd, 2026, 9:00 AM - 10:00 AM",
            ],
            is_time_flexible=True,
            location="The Alan Turing Institute, London",
        ),
        "expected": {
            "decision": "accept",
            "priority": "high",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "AI safety top priority",
                "Monday 1:30 PM slot available",
                "international experts",
                "key stakeholders",
            ],
        },
    },
    # ========== CASE 9: Vague Request - REQUEST_MORE_INFO BUT COULD ALSO BE DECLINE AS SPECULATIVE ==========
    {
        "test_id": "triage_009",
        "description": "Insufficient detail to assess strategic value",
        "invitation": Invitation(
            document_id="inv_009",
            event_type=EventType.MEETING,
            host_org="Innovation Consultancy Ltd",
            purpose="Discussion about innovation opportunities",
            event_summary="We'd like to brief you on some innovation opportunities we've identified in the tech sector.",
            topics=["innovation", "tech"],
            proposed_times=["Next week, flexible"],
            is_time_flexible=True,
            location="TBC",
        ),
        "expected": {
            "decision": "request_more_info",
            "priority": "low",
            "should_mention_calendar": False,
            "key_reasoning_points": [
                "unclear strategic value",
                "need specific agenda",
                "who will attend",
                "what opportunities",
                "Private Office assessment needed",
            ],
        },
    },
    # ========== CASE 10: Overnight Travel - Unless Critical - DECLINE UNLESS CAN DEFER? ==========
    {
        "test_id": "triage_010",
        "description": "Conference requires overnight travel - not strategically critical enough",
        "invitation": Invitation(
            document_id="inv_010",
            event_type=EventType.CONFERENCE,
            host_org="European Tech Innovation Summit",
            purpose="Speaking slot at European tech conference",
            event_summary="Two-day conference in Edinburgh. Minister invited to give 20-minute keynote on UK tech innovation landscape. 300+ attendees from across Europe.",
            topics=["tech innovation", "international", "European"],
            proposed_times=["Tuesday, February 10th, 2026, 9:00 AM (requires travel Monday evening)"],
            is_time_flexible=False,
            location="Edinburgh, Scotland",
        ),
        "expected": {
            "decision": "decline",
            "priority": "medium",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "overnight travel required",
                "not strategically critical",
                "conflicts with UKRI allocations",
                "preference against overnight travel",
            ],
        },
    },
    # ========== CASE 11: Corporate Hospitality - Against Preference - DECLINE ==========
    {
        "test_id": "triage_011",
        "description": "Corporate hospitality event violates gift/hospitality preference",
        "invitation": Invitation(
            document_id="inv_011",
            event_type=EventType.RECEPTION,
            host_org="Major Tech Corporation",
            purpose="VIP dinner for government and industry leaders",
            event_summary="Exclusive dinner hosted by CEO for select government ministers and tech industry leaders. Discussion on UK-company partnership opportunities.",
            topics=["industry collaboration", "partnerships"],
            proposed_times=["Wednesday, February 11th, 2026, 7:00 PM - 10:00 PM"],
            is_time_flexible=False,
            location="Private Members Club, London",
        ),
        "expected": {
            "decision": "decline",
            "priority": "low",
            "should_mention_calendar": False,
            "key_reasoning_points": [
                "corporate hospitality",
                "ministerial preference",
                "no gifts or hospitality",
                "not appropriate",
            ],
        },
    },
    # ========== CASE 12: Research Investment - Strategic Priority - ACCEPT ==========
    {
        "test_id": "triage_012",
        "description": "Science and research investment roundtable - top priority, good timing",
        "invitation": Invitation(
            document_id="inv_012",
            event_type=EventType.MEETING,
            host_org="Campaign for Science and Engineering (CaSE)",
            purpose="Research funding strategy roundtable",
            event_summary="Leading scientists and research leaders discussing UK research investment strategy, funding sustainability, and international competitiveness. Parliamentary and Science Committee chair attending.",
            topics=["research investment", "science funding", "research ecosystem"],
            proposed_times=["Wednesday, February 4th, 2026, 11:00 AM - 12:00 PM"],
            is_time_flexible=True,
            location="Houses of Parliament, Westminster",
        ),
        "expected": {
            "decision": "defer",
            "priority": "high",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "science and research investment top priority",
                "conflicts with Oxford-Cambridge meeting",
                "suggest 12:00 PM or afternoon",
                "key stakeholders",
            ],
        },
    },
    # ========== CASE 13: International Delegation - Prioritise - ACCEPT ==========
    {
        "test_id": "triage_013",
        "description": "International AI delegation - priority preference justifies rescheduling",
        "invitation": Invitation(
            document_id="inv_013",
            event_type=EventType.MEETING,
            host_org="US Department of Commerce",
            purpose="Bilateral on US-UK AI safety cooperation",
            event_summary="Senior US government delegation visiting UK to discuss AI safety cooperation framework, governance alignment, and joint research initiatives. Rare high-level bilateral opportunity.",
            topics=["AI safety", "international", "US-UK cooperation", "governance"],
            proposed_times=["Tuesday, February 10th, 2026, 11:00 AM - 12:30 PM"],
            is_time_flexible=False,
            location="DSIT Offices, London",
        ),
        "expected": {
            "decision": "accept",
            "priority": "high",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "AI safety top priority",
                "international delegation",
                "US-UK cooperation strategic",
                "worth rescheduling quantum skills meeting",
            ],
        },
    },
    # ========== CASE 14: Regional Development - Suitable for Delegation - DELEGATE ==========
    {
        "test_id": "triage_014",
        "description": "Regional tech event - appropriate for junior minister delegation",
        "invitation": Invitation(
            document_id="inv_014",
            event_type=EventType.SITE_VISIT,
            host_org="Manchester Digital",
            purpose="Tour of Manchester tech cluster and startup hub",
            event_summary="Half-day tour of Manchester's growing tech sector including startup incubator visits and roundtable with local tech companies. Request for Minister to provide opening remarks.",
            topics=["regional development", "tech startups", "skills"],
            proposed_times=["Thursday, February 12th, 2026, 10:00 AM - 2:00 PM"],
            is_time_flexible=True,
            location="Manchester",
        ),
        "expected": {
            "decision": "delegate",
            "priority": "medium",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "regional development",
                "suitable for junior minister",
                "conflicts with ARIA oversight",
                "good visibility opportunity for delegation",
            ],
        },
    },
    # ========== CASE 15: Perfect Strategic Fit - Monday Morning - ACCEPT ==========
    {
        "test_id": "triage_015",
        "description": "University research ecosystem discussion - perfect fit on Monday",
        "invitation": Invitation(
            document_id="inv_015",
            event_type=EventType.MEETING,
            host_org="Universities UK",
            purpose="Strategic discussion on strengthening research ecosystems",
            event_summary="University leaders want focused discussion on strengthening research ecosystems: infrastructure investment, talent pipeline, international collaboration, and funding sustainability. Direct input for university research ecosystem priority.",
            topics=["universities", "research ecosystem", "talent", "infrastructure"],
            proposed_times=["Monday, February 9th, 2026, 10:30 AM - 11:30 AM"],
            is_time_flexible=True,
            location="Universities UK, London",
        ),
        "expected": {
            "decision": "accept",
            "priority": "high",
            "should_mention_calendar": True,
            "key_reasoning_points": [
                "university research ecosystem top priority",
                "space science can be rescheduled",
                "Monday timing preferred",
                "key stakeholders",
                "worth moving medium-priority conflict",
            ],
        },
    },
]


def get_test_case(test_id: str) -> dict:
    """Get a specific test case by ID."""
    return next((tc for tc in TRIAGE_TEST_CASES if tc["test_id"] == test_id), None)


def get_test_cases_by_decision(decision: str) -> list[dict]:
    """Get all test cases with expected decision type."""
    return [tc for tc in TRIAGE_TEST_CASES if tc["expected"]["decision"] == decision]


def get_test_cases_with_conflicts() -> list[dict]:
    """Get test cases that have calendar conflicts."""
    return [tc for tc in TRIAGE_TEST_CASES if len(tc["calendar_events"]) > 0]
