# Box 2.0

AI tools for private office workflows. Currently includes a **triage** module that processes ministerial correspondence — classifying documents, extracting structured data, triaging decisions, and drafting responses.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:co-cddo/gds-idea-box2.0.git
cd gds-idea-box2.0
uv sync
```

## Development

### Running tests

Tests are split into two directories:

```
tests/
  unit/           # fast, no external dependencies
  integration/    # calls live LLM via AWS Bedrock
```

```bash
uv run pytest tests/unit/          # unit tests only (what CI runs)
uv run pytest tests/integration/   # integration tests only (requires AWS)
uv run pytest                      # everything (integration auto-skips without creds)
```

Integration tests require AWS credentials. Without them they are automatically skipped:

```bash
export AWS_PROFILE=bedrock-dev
uv run pytest tests/integration/
```

### Linting and formatting

```bash
uv run ruff check src/ tests/       # lint
uv run ruff format src/ tests/       # format
uv run ruff check --fix src/ tests/  # auto-fix
```

### Running examples

The `examples/` directory contains runnable scripts demonstrating each pipeline stage:

```bash
AWS_PROFILE=bedrock-dev uv run python examples/example_email_end_to_end.py
AWS_PROFILE=bedrock-dev uv run python examples/example_triage.py
```

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
tests/
  unit/triage/                   # unit tests mirroring src/box2/triage/
  integration/triage/            # LLM integration tests
examples/                        # runnable example scripts
evaluation/                      # evaluation notebooks and datasets
```
