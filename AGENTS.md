# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project Overview

Python library for AI-powered ministerial correspondence processing (triage, extraction,
redaction, redrafting). Uses **pydantic-ai** agents on **AWS Bedrock** (Claude models) with
**Pydantic** for structured outputs. Package manager is **uv**; build system is **Hatchling**.

Source layout: `src/box2/` (library code), `tests/unit/`, `tests/integration/`, `examples/`.

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

CI runs lint, format check, and unit tests across Python 3.11-3.14. Integration tests
are never run in CI (no AWS credentials). The CI also enforces a version bump in
`pyproject.toml` before merging to `main`.

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

All data models live in `src/box2/triage/models/` and are re-exported from `__init__.py`.
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
- **Version bump required** -- every PR must increment the version in `pyproject.toml`.

## Receiver v2 Design Plan (pending implementation)

The current receiver (`src/box2/receiver/`) is a minimal webhook endpoint with a placeholder
`dispatch()`. The v2 design replaces this with a production-ready app factory that handles
the full notification-to-handler pipeline.

### Deployment target

API Gateway → Lambda (Mangum wrapping FastAPI). The existing FastAPI app works unchanged
with Mangum as the Lambda handler entry point.

### Application workflow

1. A file is uploaded to a **Files List** in SharePoint.
2. Graph sends a webhook notification to the backend.
3. The backend queries the list for recently changed items, identifies the new file, and
   processes it (triage, extraction, etc.).
4. The backend creates items in one of several **Processing Lists**.
5. A human reviews and comments/edits the item in SharePoint.
6. Graph sends a webhook notification to the backend.
7. The backend detects the human edit, runs a workflow, and writes to an **Output List**.

### Key design decisions

- **Endpoint-per-subscription** — each subscription points at its own URL
  (e.g. `/file_uploaded`, `/item_reviewed`). Graph does the routing.
- **No delta tokens** — use a rolling time window (`lookback_minutes`, default 2) to
  query recently changed items via `$filter=lastModifiedDateTime gt '{cutoff}'`.
- **Self-write filtering** — the app only creates items in processing lists, never updates
  them. Items where `lastModifiedBy.application.id` matches the service principal are
  skipped. Configurable per route (`filter_self=True/False`).
- **Item-level dedup** — key is `{list_id}:{item_id}:{lastModifiedDateTime}`. Prevents
  the same edit from being processed twice when overlapping lookback windows span
  consecutive notifications. Uses the same `DeduplicationStore` protocol.
- **Record before calling handler** — the dedup record is written *before* the handler
  runs, giving at-most-once semantics. This is required because handlers call LLMs and
  cannot guarantee idempotency.
- **DynamoDB dedup required for Lambda** — concurrent Lambda invocations share no memory.
  `DynamoDedup` with conditional writes (`attribute_not_exists(pk)`) gives atomic
  at-most-once semantics. `InMemoryDedup` is fine for local dev only.
- **Configurable filter field** — `createdDateTime` for new-item detection (Files List),
  `lastModifiedDateTime` for edit detection (Processing Lists).

### App factory API

```python
from box2.receiver import create_app, ReceiverConfig, WebhookRoute

config = ReceiverConfig(
    client_state="my-shared-secret",
    app_identity="<service-principal-app-id>",
    lookback_minutes=2,
)

app = create_app(
    config=config,
    routes=[
        WebhookRoute(
            path="/file_uploaded",
            list_client=files_list,
            handler=process_new_file,
            filter_self=False,
            filter_field="createdDateTime",
        ),
        WebhookRoute(
            path="/item_reviewed",
            list_client=processing_list,
            handler=process_human_edit,
            filter_self=True,
            filter_field="lastModifiedDateTime",
        ),
    ],
)
```

### Per-request flow (handled by the factory for every route)

```
Notification arrives
    │
    ├─ Validation handshake? → echo token, return
    │
    ├─ Client state check → reject silently if wrong
    │
    ├─ Notification-level dedup → skip if duplicate notification
    │
    ▼
Query list: items where {filter_field} > {now - lookback_minutes}, $expand=fields
    │
    ├─ filter_self=True? → drop items where lastModifiedBy.application.id == app_identity
    │
    ├─ Item-level dedup → drop items already processed (same item + same lastModifiedDateTime)
    │
    ▼
For each remaining item:
    ├─ Record in dedup store (before handler, to prevent concurrent processing)
    └─ Call handler(item)
```

### Handler signature

Handlers are called once per matching item. They receive a single item dict (the full
Graph API response with fields expanded):

```python
async def process_human_edit(item: dict) -> None:
    """Called once per item modified by a human."""
    status = item["fields"]["Status"]
    # ... run workflow, write to output list
```

### WebhookRoute dataclass

```python
@dataclass
class WebhookRoute:
    path: str                                       # URL path, e.g. "/file_uploaded"
    list_client: ListClient                         # queries items after notification
    handler: Callable[[dict], Awaitable[None]]      # called once per matching item
    filter_self: bool = True                        # skip items modified by the app
    filter_field: str = "lastModifiedDateTime"      # or "createdDateTime" for new items
```

### Files to modify/create

- `src/box2/receiver/config.py` — add `app_identity: str`, `lookback_minutes: int = 2`
- `src/box2/receiver/routes.py` (new) — `WebhookRoute` dataclass
- `src/box2/receiver/app.py` — refactor `create_app()` to accept routes, generate
  endpoints dynamically, implement the per-request flow above
- `src/box2/receiver/handlers.py` — replace placeholder `dispatch()` with the item
  query + filter + dedup + handler-call pipeline
- `src/box2/receiver/dedup.py` — extend for item-level dedup (same protocol, different keys)
- `src/box2/receiver/__init__.py` — export `WebhookRoute`
- `examples/sharepoint/webhook_e2e.py` — update for new `create_app()` signature
- `examples/sharepoint/run_receiver.py` — update similarly
- Tests — update existing, add new for item filtering, dedup, routing

### Not yet implemented (future work)

- `DynamoDedup` — protocol-based, conditional writes for Lambda concurrency safety
- Mangum adapter / Lambda handler entry point
- Dead-letter / retry mechanism for failed handler invocations
- Specific workflow handler implementations (triage, extraction, etc.)
