"""Tests for to_sharepoint_fields, from_sharepoint_fields, and round-trip serialisation."""

from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field

from box2.pipeline.mappers import from_sharepoint_fields, to_sharepoint_fields

# ===== Test models =====


class MockSharepointModel(BaseModel):
    """Minimal model for testing to_sharepoint_fields."""

    title: str = Field(description="Title field")
    notes: str | None = Field(default=None, description="Optional notes")
    tags: list[str] = Field(default_factory=list, description="Plain text tags")
    links: list[AnyHttpUrl] = Field(default_factory=list, description="Reference URLs")
    created: datetime = Field(description="Creation timestamp")
    score: float = Field(default=0.0, description="Numeric score")


class MockModelWithLongFieldName(BaseModel):
    """Model with a field name exceeding 32 characters."""

    title: str = Field(description="Title")
    ai_routing_alternative_directorate: str | None = Field(default=None, description="38 chars")


class RoundTripModel(BaseModel):
    """Model covering all field types handled by the serialisation pair."""

    title: str = Field(description="Title field")
    name: str = Field(description="Plain string")
    notes: str | None = Field(default=None, description="Optional string")
    tags: list[str] = Field(default_factory=list, description="Plain text list")
    links: list[AnyHttpUrl] = Field(default_factory=list, description="URL list")
    is_active: bool = Field(default=True, description="Boolean flag")
    created: datetime = Field(description="Datetime field")
    priority: Literal["high", "medium", "low"] = Field(default="medium", description="Literal field")
    a_very_long_field_name_that_exceeds_limit: str | None = Field(
        default=None, description="43-char field name, truncated to 32"
    )


# ===== to_sharepoint_fields =====


def test_title_mapped_to_capital_t():
    """Title field should be keyed as 'Title' for SharePoint's built-in column."""
    model = MockSharepointModel(title="Test", created=datetime(2025, 1, 1))
    fields = to_sharepoint_fields(model)
    assert "Title" in fields
    assert fields["Title"] == "Test"
    assert "title" not in fields


def test_none_values_omitted():
    """None values should be dropped from the output."""
    model = MockSharepointModel(title="Test", notes=None, created=datetime(2025, 1, 1))
    fields = to_sharepoint_fields(model)
    assert "notes" not in fields


def test_plain_list_joined_with_semicolons():
    """list[str] fields should be semicolon-delimited."""
    model = MockSharepointModel(title="Test", tags=["alpha", "beta", "gamma"], created=datetime(2025, 1, 1))
    fields = to_sharepoint_fields(model)
    assert fields["tags"] == "alpha; beta; gamma"


def test_url_list_formatted_as_html_links():
    """list[AnyHttpUrl] fields should be formatted as HTML anchor tags."""
    model = MockSharepointModel(
        title="Test",
        links=["https://www.gov.uk/guidance/example", "https://example.com/page"],
        created=datetime(2025, 1, 1),
    )
    fields = to_sharepoint_fields(model)
    expected = (
        '<a href="https://www.gov.uk/guidance/example">https://www.gov.uk/guidance/example</a>'
        "<br>"
        '<a href="https://example.com/page">https://example.com/page</a>'
    )
    assert fields["links"] == expected


def test_empty_url_list_omits_field():
    """An empty URL list should still produce a value (empty string)."""
    model = MockSharepointModel(title="Test", links=[], created=datetime(2025, 1, 1))
    fields = to_sharepoint_fields(model)
    assert fields["links"] == ""


def test_datetime_serialised_as_isoformat():
    """datetime fields should be ISO-formatted strings."""
    dt = datetime(2025, 6, 15, 10, 30)
    model = MockSharepointModel(title="Test", created=dt)
    fields = to_sharepoint_fields(model)
    assert fields["created"] == "2025-06-15T10:30:00"


def test_float_serialised_as_string():
    """float fields should be converted to strings."""
    model = MockSharepointModel(title="Test", score=3.14, created=datetime(2025, 1, 1))
    fields = to_sharepoint_fields(model)
    assert fields["score"] == "3.14"


def test_long_field_name_truncated_to_32_chars():
    """Field names longer than 32 characters should be truncated."""
    model = MockModelWithLongFieldName(
        title="Test",
        ai_routing_alternative_directorate="Cross-Government S&T",
    )
    fields = to_sharepoint_fields(model)

    # 38-char field name should be truncated to 32
    truncated = "ai_routing_alternative_directora"
    assert len(truncated) == 32
    assert truncated in fields
    assert fields[truncated] == "Cross-Government S&T"

    # Full name should NOT be present
    assert "ai_routing_alternative_directorate" not in fields


# ===== Round-trip: to_sharepoint_fields → from_sharepoint_fields =====


def test_round_trip_all_fields():
    """A fully populated model should survive serialise → deserialise unchanged."""
    original = RoundTripModel(
        title="AI Safety Summit",
        name="summit-2026",
        notes="Important event",
        tags=["AI Safety", "International", "Policy"],
        links=["https://www.gov.uk/guidance", "https://example.com/page"],
        is_active=True,
        created=datetime(2026, 3, 15, 10, 30),
        priority="high",
        a_very_long_field_name_that_exceeds_limit="truncated value",
    )

    serialised = to_sharepoint_fields(original)
    restored = from_sharepoint_fields(serialised, RoundTripModel)

    assert restored.title == original.title
    assert restored.name == original.name
    assert restored.notes == original.notes
    assert restored.tags == original.tags
    assert [str(u) for u in restored.links] == [str(u) for u in original.links]
    assert restored.is_active == original.is_active
    assert restored.created == original.created
    assert restored.priority == original.priority
    assert restored.a_very_long_field_name_that_exceeds_limit == original.a_very_long_field_name_that_exceeds_limit


def test_round_trip_list_str():
    """list[str] fields should survive semicolon join and split."""
    original = RoundTripModel(
        title="Test",
        name="test",
        tags=["alpha", "beta", "gamma"],
        created=datetime(2025, 1, 1),
    )

    restored = from_sharepoint_fields(to_sharepoint_fields(original), RoundTripModel)
    assert restored.tags == ["alpha", "beta", "gamma"]


def test_round_trip_list_url():
    """list[AnyHttpUrl] fields should survive HTML encoding and extraction."""
    original = RoundTripModel(
        title="Test",
        name="test",
        links=["https://www.gov.uk/guidance/ai", "https://example.com/report?id=42&lang=en"],
        created=datetime(2025, 1, 1),
    )

    restored = from_sharepoint_fields(to_sharepoint_fields(original), RoundTripModel)
    assert [str(u) for u in restored.links] == [str(u) for u in original.links]


def test_round_trip_empty_list_str():
    """An empty list[str] should survive the round-trip as an empty list."""
    original = RoundTripModel(
        title="Test",
        name="test",
        tags=[],
        created=datetime(2025, 1, 1),
    )

    restored = from_sharepoint_fields(to_sharepoint_fields(original), RoundTripModel)
    assert restored.tags == []


def test_round_trip_empty_list_url():
    """An empty list[AnyHttpUrl] should survive the round-trip as an empty list."""
    original = RoundTripModel(
        title="Test",
        name="test",
        links=[],
        created=datetime(2025, 1, 1),
    )

    restored = from_sharepoint_fields(to_sharepoint_fields(original), RoundTripModel)
    assert restored.links == []


def test_round_trip_none_optional():
    """None optional fields should be omitted during serialise and default on deserialise."""
    original = RoundTripModel(
        title="Test",
        name="test",
        notes=None,
        created=datetime(2025, 1, 1),
    )

    serialised = to_sharepoint_fields(original)
    assert "notes" not in serialised

    restored = from_sharepoint_fields(serialised, RoundTripModel)
    assert restored.notes is None


def test_round_trip_populated_optional():
    """A populated optional field should survive the round-trip."""
    original = RoundTripModel(
        title="Test",
        name="test",
        notes="Some important notes",
        created=datetime(2025, 1, 1),
    )

    restored = from_sharepoint_fields(to_sharepoint_fields(original), RoundTripModel)
    assert restored.notes == "Some important notes"


def test_round_trip_bool():
    """Boolean fields should survive the round-trip."""
    for value in (True, False):
        original = RoundTripModel(
            title="Test",
            name="test",
            is_active=value,
            created=datetime(2025, 1, 1),
        )

        restored = from_sharepoint_fields(to_sharepoint_fields(original), RoundTripModel)
        assert restored.is_active is value


def test_round_trip_datetime():
    """datetime fields should survive ISO serialise and Pydantic coercion."""
    dt = datetime(2026, 6, 15, 14, 30, 45)
    original = RoundTripModel(
        title="Test",
        name="test",
        created=dt,
    )

    restored = from_sharepoint_fields(to_sharepoint_fields(original), RoundTripModel)
    assert restored.created == dt


def test_round_trip_literal():
    """Literal-typed fields should survive the round-trip."""
    for value in ("high", "medium", "low"):
        original = RoundTripModel(
            title="Test",
            name="test",
            priority=value,
            created=datetime(2025, 1, 1),
        )

        restored = from_sharepoint_fields(to_sharepoint_fields(original), RoundTripModel)
        assert restored.priority == value


def test_round_trip_title_key_mapping():
    """The title field should map Title → title through the round-trip."""
    original = RoundTripModel(
        title="My Important Title",
        name="test",
        created=datetime(2025, 1, 1),
    )

    serialised = to_sharepoint_fields(original)
    assert "Title" in serialised
    assert "title" not in serialised

    restored = from_sharepoint_fields(serialised, RoundTripModel)
    assert restored.title == "My Important Title"


def test_round_trip_truncated_field_name():
    """A field name > 32 chars should survive truncation through the round-trip."""
    original = RoundTripModel(
        title="Test",
        name="test",
        a_very_long_field_name_that_exceeds_limit="important value",
        created=datetime(2025, 1, 1),
    )

    serialised = to_sharepoint_fields(original)
    # The 43-char field name should be truncated to 32
    truncated_key = "a_very_long_field_name_that_exce"
    assert len(truncated_key) == 32
    assert truncated_key in serialised

    restored = from_sharepoint_fields(serialised, RoundTripModel)
    assert restored.a_very_long_field_name_that_exceeds_limit == "important value"
