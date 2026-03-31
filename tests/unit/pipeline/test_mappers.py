from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, Field

from src.box2.pipeline.mappers import to_sharepoint_fields


class MockSharepointModel(BaseModel):
    """Minimal model for testing to_sharepoint_fields."""

    title: str = Field(description="Title field")
    notes: str | None = Field(default=None, description="Optional notes")
    tags: list[str] = Field(default_factory=list, description="Plain text tags")
    links: list[AnyHttpUrl] = Field(default_factory=list, description="Reference URLs")
    created: datetime = Field(description="Creation timestamp")
    score: float = Field(default=0.0, description="Numeric score")


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
