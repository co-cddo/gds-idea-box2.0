import json

from pydantic import BaseModel, Field

from box2.triage.exceptions import PersonaError


class MinisterPersona(BaseModel):
    """Configuration for a specific minister including their portfolio topics."""

    name: str = Field(description="Minister's name or title")

    role: str = Field(description="Official role/position")

    priorities: list[str] = Field(description="Top policy priorities for decision-making")

    responsibilities: dict[str, list[str]] = Field(
        description=(
            "Policy areas and topics by department (e.g., DSIT, DESNZ). Used both for context and categorization."
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
        """
        Load persona from JSON file.

        Args:
            path: Path to JSON file containing persona configuration

        Returns:
            MinisterPersona instance

        Raises:
            PersonaError: If file not found, JSON invalid, or validation fails
        """
        try:
            with open(path) as f:
                data = json.load(f)
        except FileNotFoundError as e:
            raise PersonaError(
                f"Persona file not found: {path}",
                persona_path=path,
                cause=e,
            ) from e
        except json.JSONDecodeError as e:
            raise PersonaError(
                f"Invalid JSON in persona file: {path} (line {e.lineno}, col {e.colno})",
                persona_path=path,
                cause=e,
            ) from e
        except Exception as e:
            raise PersonaError(
                f"Failed to read persona file: {path} - {str(e)}",
                persona_path=path,
                cause=e,
            ) from e

        try:
            return cls(**data)
        except Exception as e:
            raise PersonaError(
                f"Invalid persona data in {path}: {str(e)}",
                persona_path=path,
                cause=e,
            ) from e
