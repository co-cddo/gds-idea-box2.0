# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project Overview

Python library for AI-powered ministerial correspondence processing (triage, extraction,
redaction, redrafting). Uses **pydantic-ai** agents on **AWS Bedrock** (Claude models) with
**Pydantic** for structured outputs. Package manager is **uv**; build system is **Hatchling**.

Source layout: `src/box2/` (library code), `tests/unit/`, `tests/integration/`, `examples/`.

SharePoint / Microsoft Graph access (`SharePointSession`, `ListClient`, `DocsClient`,
`WebhookClient`, `generate_graph_schema`) and the webhook receiver framework
(`gds_idea_sharepoint.receiver`) live in the separate `gds-idea-sharepoint` package (repo
`co-cddo/gds-idea-pkg-sharepoint`), installed from the GDS IDEA package index. Change them there,
not here. See "Application Architecture" below.

## Build and Run Commands

All commands use `uv run`. Install dependencies first with `uv sync`.

```sh
# Lint
uv run ruff check src/ tests/
uv run ruff check --fix src/ tests/      # auto-fix

# Format
uv run ruff format src/ tests/
uv run ruff format --check src/ tests/    # check only (CI uses this)

# Run all unit tests
uv run pytest tests/unit/ -v

# Run a single test file
uv run pytest tests/unit/triage/test_calendar.py -v

# Run a single test function
uv run pytest tests/unit/triage/test_calendar.py::test_weekends_are_empty -v

# Run tests matching a keyword
uv run pytest tests/unit/ -k "calendar" -v

# Integration tests (require AWS credentials)
AWS_PROFILE=bedrock-dev uv run pytest tests/integration/ -v

# Run all tests (unit + integration; integration auto-skipped without creds)
uv run pytest -v
```

CI runs lint, format check, and unit tests across Python 3.12-3.14. Integration tests
are never run in CI (no AWS credentials). Versions are not set by hand: they come from git
tags (hatch-vcs), and merging to `main` auto-tags a release (patch by default; label the PR
`bump:minor` or `bump:major` to change the level).

## Code Style

### Formatting and Linting

Ruff handles both linting and formatting. All config lives in `pyproject.toml`.

- **Line length:** 120 characters (E501 is ignored; ruff format handles wrapping)
- **Target version:** Python 3.12
- **Enabled rule sets:** E (pycodestyle), F (pyflakes), I (isort), B (bugbear),
  UP (pyupgrade), N (pep8-naming), A (builtins shadowing), PT (pytest style)

### Imports

Sorted by isort (via ruff). Group order: stdlib, third-party, local. Multi-line imports
are allowed (`force-single-line = false`), and `combine-as-imports = true`.

```python
import logging
from datetime import datetime, timedelta
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from box2.triage.config import model
from box2.triage.exceptions import ExtractionError, TriageError
from box2.triage.models import CalendarEvent, Invitation, MinisterPersona
```

### Type Annotations

- Annotate all function signatures and return types.
- Use modern union syntax: `str | None` not `Optional[str]`, `list[str]` not `List[str]`.
- Use `Literal` for constrained strings, `Protocol` for interfaces.
- The package includes a `py.typed` marker (PEP 561).

### Naming Conventions

- **Modules/files:** `snake_case` -- `pii_redaction.py`, `action_extraction.py`
- **Functions/variables:** `snake_case` -- `extract_invitation()`, `safe_doc`
- **Classes:** `PascalCase` -- `PIIRedactor`, `SafeDocument`, `TriagedDecision`
- **Constants:** `UPPER_SNAKE_CASE` -- `SONNET_45`, `GRAPH_BASE_URL`
- **Private methods:** underscore prefix -- `_build_template()`, `_merge_pii()`

### Docstrings

Google-style docstrings. Every module has a module-level docstring. Functions include
`Args:`, `Returns:`, and `Raises:` sections where applicable.

```python
"""Centralized PII extraction and redaction logic."""

def redact(text: str, entities: list[str]) -> str:
    """Replace PII entities with placeholders.

    Args:
        text: The input text containing PII.
        entities: List of PII strings to redact.

    Returns:
        Text with PII replaced by [REDACTED] placeholders.

    Raises:
        ValueError: If text is empty.
    """
```

### Logging

Every module declares a module-level logger: `logger = logging.getLogger(__name__)`.

### Error Handling

Custom exception hierarchy rooted in domain base classes. Each exception carries
contextual attributes (`document_id`, `cause`, `text_preview`, etc.).

For LLM-calling functions, follow this pattern:

```python
try:
    result = await agent.run(prompt, deps=deps)
    return result.output
except (ModelRetry, UnexpectedModelBehavior) as e:
    logger.error(f"LLM failed: {e}", exc_info=True)
    raise DomainSpecificError("descriptive message", cause=e) from e
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise DomainSpecificError("descriptive message", cause=e) from e
```

Always chain exceptions with `from e`. Always log before re-raising.

### Agent (LLM) Pattern

pydantic-ai agents follow a consistent structure in each module:

1. Define a module-level system prompt as a string constant.
2. Create `Agent(model=model, output_type=PydanticModel, deps_type=ContextType)`.
3. Use `@agent.system_prompt` for dynamic prompt injection.
4. Use `@agent.tool` for tools the agent can call (e.g., calendar lookup).
5. Wrap invocation in an `async` function with the error handling pattern above.

### Pydantic Models

LLM and domain data models live in `src/box2/triage/models/` and are re-exported from `__init__.py`.
The SharePoint list-schema models (`SharepointInvitation`, `SharepointSubmission`, `SharepointAction`,
`SharepointInvitationQA`, `SharepointPQs`) are persistence shapes, not domain objects: they live in
`src/box2/pipeline/schemas/`, next to the mappers that convert to and from them.
Use `BaseModel` with `Field(...)` for validation. Use union types for classification
results (e.g., `Invitation | NotInvitation`).

## Testing

### Structure

Tests mirror source layout. Unit tests in `tests/unit/`, integration tests in
`tests/integration/`. Integration tests are auto-skipped when AWS credentials are absent
(handled by `tests/integration/conftest.py`).

### Conventions

- **No test classes** -- use plain `def test_*()` functions.
- **Section comments** group related tests: `# ===== Section Name =====`
- **Docstrings on every test** explaining what is being validated.
- **Fixtures** via `@pytest.fixture` for shared setup.
- **Parametrize** with `@pytest.mark.parametrize` for data-driven tests.
- **Async tests** use `pytest.mark.anyio` (not `pytest-asyncio`).
- **Integration marker:** `pytestmark = [pytest.mark.integration, pytest.mark.anyio]`.
- **Pydantic validation tests** use `pytest.raises(ValidationError)`.
- Integration tests use **fuzzy matching** (`fuzzywuzzy`) with thresholds for
  non-deterministic LLM output assertions.

### Running Tests Before Committing

Always run lint and unit tests before committing:

```sh
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run pytest tests/unit/ -v
```

## Project Conventions

- **All config in `pyproject.toml`** -- no separate config files for ruff, pytest, etc.
- **PII-first design** -- text is always redacted before being sent to LLMs.
- **Async throughout** -- all LLM-calling functions are `async`.
- **Deterministic where possible** -- e.g., submission replies use templates, not LLMs.
- **Versioning is automatic** -- do not edit a version in `pyproject.toml`. Releases are tagged on merge to `main`; use the `bump:minor` / `bump:major` PR labels to raise the level.

## Application Architecture (AWS Lambda)

box2 is deployed as a single AWS Lambda: API Gateway -> Mangum -> FastAPI. The Lambda entry
point is `box2.receiver.lambda_handler.handler` (this path is configured in the deployment, so
do not move it).

### Where the code lives

| Concern | Location |
|---|---|
| SharePoint / Graph client, webhook subscriptions | `gds-idea-sharepoint` (`gds_idea_sharepoint`) |
| Webhook receiver framework (`create_app`, `WebhookRoute`, dedup) | `gds-idea-sharepoint` (`gds_idea_sharepoint.receiver`, extra `[receiver]` / `[lambda]`) |
| LLM triage, extraction, redaction, models | `src/box2/triage/` |
| Orchestration, SharePoint list schemas and mappers | `src/box2/pipeline/` (`schemas/`, `mappers.py`) |
| This application's handlers and Lambda wiring | `src/box2/receiver/` (`route_handlers.py`, `lambda_handler.py`) |

The framework and the SharePoint client are changed in `co-cddo/gds-idea-pkg-sharepoint`, not here.
box2 pins a minimum version in `pyproject.toml`.

### Workflow

1. A file is uploaded to the documents library.
2. Graph calls `/file_uploaded`. The handler downloads the file, runs `triage_file`, and writes an
   invitation to the **QA Invitations** list or a submission to the **Submissions** list.
3. Private office reviews a QA item (`/qa_reviewed`). Approved items are copied to **Invitations**;
   rejected items to **Rejected Invitations**; both are then deleted from the QA list.
4. The minister reviews an invitation or submission (`/invitation_reviewed`, `/submission_reviewed`).
   The handler extracts actions with an LLM and writes one row per action to the **Actions** list.

### Receiver design decisions

- **Endpoint per subscription** -- each Graph subscription points at its own route; Graph does the routing.
- **No delta tokens** -- each notification triggers `get_recent(minutes=LOOKBACK_MINUTES)` (default 2).
- **Self-write filtering** -- routes that the app also writes to use `filter_self=True`, which skips
  items where `lastModifiedBy.application.id` equals `APP_IDENTITY`.
- **Item-level dedup** -- key is `item:{route}:{item_id}:{lastModifiedDateTime}`, so overlapping
  lookback windows do not reprocess the same edit.
- **Record before calling the handler** -- gives at-most-once handling, which is required because
  handlers call LLMs and are not idempotent.
- **DynamoDB dedup on Lambda** -- concurrent invocations share no memory; `DynamoDedup` uses
  conditional writes. `InMemoryDedup` is for local development only.

Handlers are `async def handler(item: dict) -> None`, called once per matching item with the full
Graph item (fields expanded).

### Not yet implemented

- Dead-letter / retry for failed handler invocations (a failed item is not retried, because it is
  already recorded in the dedup store).
