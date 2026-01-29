import json

from pydantic import BaseModel, Field


class MinisterPersona(BaseModel):
    """Configuration for a specific minister including their portfolio topics."""

    name: str = Field(description="Minister's name or title")

    role: str = Field(description="Official role/position")

    priorities: list[str] = Field(
        description="Top policy priorities for decision-making"
    )

    responsibilities: dict[str, list[str]] = Field(
        description=(
            "Policy areas and topics by department (e.g., DSIT, DESNZ). "
            "Used both for context and categorization."
        )
    )

    preferences: list[str] = Field(
        default_factory=list,
        description=(
            "General preferences and constraints (e.g., 'no corporate hospitality', "
            "'prefer morning meetings', 'avoid Fridays')"
        ),
    )

    @classmethod
    def from_json_file(cls, path: str) -> "MinisterPersona":
        """Load persona from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)
