# Box 2.0

AI tools for private office workflows. Currently includes a **triage** module that processes ministerial correspondence — classifying documents, extracting structured data, triaging decisions, and drafting responses — a **sharepoint** module for authenticated access to SharePoint via Microsoft Graph API (lists and document libraries), and a **receiver** module (FastAPI webhook endpoint) for processing Microsoft Graph change notifications.

## Installation

Install as a library dependency:

```bash
pip install box2
```

The receiver module (FastAPI webhook endpoint) is an optional extra:

```bash
pip install box2[receiver]
```

## Development setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:co-cddo/gds-idea-box2.0.git
cd gds-idea-box2.0
uv sync --all-extras
```

`--all-extras` installs everything including optional dependencies (FastAPI, uvicorn, pyngrok). This is required for development — some tests depend on the optional extras.

### Running tests

Tests are split into three tiers:

```
tests/
  unit/           # fast, no external dependencies
  integration/    # calls live LLM via AWS Bedrock / SharePoint via Graph API
  evals/          # LLM output quality assessments (TODO: migrate to proper eval framework)
```

```bash
# Unit tests (what CI runs)
uv run pytest tests/unit/ -v

# Integration tests (deterministic, requires AWS credentials)
AWS_PROFILE=bedrock-dev uv run pytest tests/integration/ -v

# Everything except evals (default -- evals are excluded by the -m "not eval" default)
uv run pytest -v

# Evals only (fuzzy/subjective quality checks, some failure expected)
AWS_PROFILE=bedrock-dev uv run pytest -m eval tests/evals/ -v
```

Integration tests require AWS credentials. Without them they are automatically skipped:

```bash
export AWS_PROFILE=bedrock-dev
uv run pytest tests/integration/
```

**Evals** assess LLM output quality (field extraction accuracy, triage decision quality,
priority calibration) using fuzzy string matching and heuristic thresholds. They are
excluded from default test runs because some failure is expected -- they measure quality
trends, not correctness. They are a placeholder until we implement a proper eval framework
with semantic similarity / LLM-as-judge scoring.

### Linting and formatting

```bash
uv run ruff check src/ tests/       # lint
uv run ruff format src/ tests/       # format
uv run ruff check --fix src/ tests/  # auto-fix
```

### Running examples

The `examples/` directory contains runnable scripts demonstrating each pipeline stage:

```bash
AWS_PROFILE=bedrock-dev uv run python examples/triage/email_end_to_end.py
AWS_PROFILE=bedrock-dev uv run python examples/triage/triage.py
uv run python examples/sharepoint/auth.py
uv run python examples/sharepoint/list_operations.py
AWS_PROFILE=bedrock-dev uv run python examples/sharepoint/lists_webhook_e2e.py
AWS_PROFILE=bedrock-dev uv run python examples/sharepoint/docs_webhook_e2e.py
uv run python examples/sharepoint/run_receiver.py
```

The webhook E2E scripts (`lists_webhook_e2e.py` and `docs_webhook_e2e.py`) run the full notification loop in a single process — they start a local FastAPI receiver, open an ngrok tunnel, create a subscription, trigger changes, and clean up. They require `NGROK_AUTH_TOKEN` in your `.env` file and AWS credentials. `run_receiver.py` starts just the receiver for manual testing.

## Versioning

Versions are derived from git tags using [hatch-vcs](https://github.com/ofek/hatch-vcs).
There is no version number in `pyproject.toml`.

**Patch releases** are created automatically when a PR is merged to `main`.
The CI increments the patch number from the latest tag (e.g. `v0.2.1` -> `v0.2.2`).

**Minor or major releases** are created by pushing a tag manually:

```bash
git tag v0.3.0 && git push --tags    # minor bump
git tag v1.0.0 && git push --tags    # major bump
```

The tag push triggers a GitHub release with auto-generated notes.

## Project structure

```
src/box2/
  triage/                        # triage module
    models/                      # Pydantic models (Invitation, Submission, etc.)
    config.py                    # AWS Bedrock / LLM configuration
    document_classifier.py
    invitation_extraction.py
    submission_extraction.py
    triage.py
    invitation_redraft.py
    action_extraction.py
    submission_reply.py
    pii_redaction.py
    file_parser.py
  sharepoint/                    # SharePoint module
    session.py                   # Auth: AWS STS -> Azure AD -> Graph API
    list_client.py               # CRUD operations on SharePoint lists
    docs_client.py               # Document library operations (drive files)
    webhook_client.py            # Microsoft Graph subscription management
    protocols.py                 # SubscribableResource protocol
    models.py                    # Subscription model
    exceptions.py                # SharePoint exception hierarchy
  receiver/                      # Webhook receiver (optional: pip install box2[receiver])
    app.py                       # FastAPI app factory
    handlers.py                  # Notification processing and dispatch
    models.py                    # Notification/NotificationPayload models
    dedup.py                     # Deduplication store (protocol + in-memory impl)
    config.py                    # ReceiverConfig
tests/
  unit/
    triage/                      # unit tests for triage module
    sharepoint/                  # unit tests for SharePoint module
    receiver/                    # unit tests for receiver module
  integration/
    triage/                      # LLM integration tests (deterministic)
    sharepoint/                  # SharePoint integration tests
  evals/
    triage/                      # LLM output quality evals (TODO: proper eval framework)
examples/
  triage/                        # triage example scripts
  sharepoint/                    # SharePoint example scripts
  data/                          # sample data for examples
```
