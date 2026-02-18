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

```bash
uv run pytest                      # unit tests (integration tests auto-skip without AWS creds)
uv run pytest -m "not integration" # unit tests only (what CI runs)
uv run pytest -m integration       # integration tests only (requires AWS)
```

Integration tests call live LLM endpoints via AWS Bedrock. They require:

```bash
export AWS_PROFILE=bedrock-dev
uv run pytest -m integration
```

Without `AWS_PROFILE` set, integration tests are automatically skipped with a message.

### Linting and formatting

```bash
uv run ruff check src/ tests/       # lint
uv run ruff format src/ tests/       # format
uv run ruff check --fix src/ tests/  # auto-fix
```

### Running examples

The `examples/` directory contains runnable scripts demonstrating each pipeline stage:

```bash
uv run python examples/example_email_end_to_end.py
uv run python examples/example_triage.py
```

These require AWS credentials (`AWS_PROFILE=bedrock-dev`).

## Project structure

```
src/box2/
  triage/               # Triage module
    models/             # Pydantic models (Invitation, Submission, etc.)
    config.py           # AWS Bedrock / LLM configuration
    document_classifier.py
    invitation_extraction.py
    submission_extraction.py
    triage.py
    invitation_redraft.py
    action_extraction.py
    submission_reply.py
    pii_redaction.py
    file_parser.py
tests/                  # Unit + integration tests
examples/               # Runnable example scripts
evaluation/             # Evaluation notebooks and datasets
```
