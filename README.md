# Box 2.0

AI tools for private office workflows. Currently includes a **triage** module that processes ministerial correspondence — classifying documents, extracting structured data, triaging decisions, and drafting responses — a **pipeline** module that maps triage results to SharePoint list schemas, and the application's AWS Lambda **receiver** handlers for Microsoft Graph change notifications. SharePoint access and the webhook receiver framework come from the separate [`gds-idea-sharepoint`](https://github.com/co-cddo/gds-idea-pkg-sharepoint) package.

## Installation

Install as a library dependency from the GDS IDEA package index (this also installs
[`gds-idea-sharepoint`](https://github.com/co-cddo/gds-idea-pkg-sharepoint)):

```bash
pip install box2 --extra-index-url https://co-cddo.github.io/gds-idea-pypi/simple/
```

The extras are:

```bash
pip install box2[pipeline]   # triage pipeline dependencies (pydantic-ai, pypdf, python-docx, pandas)
pip install box2[receiver]   # everything the AWS Lambda needs: the pipeline plus the webhook receiver (FastAPI, Mangum)
```

## Development setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:co-cddo/gds-idea-box2.0.git
cd gds-idea-box2.0
uv sync --all-extras
```

`--all-extras` installs every optional dependency (the LLM pipeline and the receiver's FastAPI and Mangum). This is required for development — some tests depend on the optional extras.

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
```

The SharePoint and webhook examples (authentication, list operations, the local receiver and the ngrok end-to-end scripts) live with the library in [`gds-idea-pkg-sharepoint`](https://github.com/co-cddo/gds-idea-pkg-sharepoint/tree/main/examples).

## Versioning

Versions are derived from git tags using [hatch-vcs](https://github.com/ofek/hatch-vcs).
There is no version number in `pyproject.toml`.

**Patch releases** are created automatically when a PR is merged to `main` — no action needed.

**Minor or major releases** are triggered by applying a label to the PR before merging:

| Label | Effect | Example |
|-------|--------|---------|
| _(none)_ | patch bump | `v0.3.8` → `v0.3.9` |
| `bump:minor` | minor bump, patch reset to 0 | `v0.3.8` → `v0.4.0` |
| `bump:major` | major bump, minor+patch reset to 0 | `v0.3.8` → `v1.0.0` |

The `Auto Release` workflow runs on every merge to `main`, computes the next version from the
latest tag and the PR's labels, and publishes a GitHub release with the built wheel and sdist.

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
  pipeline/                      # Orchestration, SharePoint list schemas and mappers
    schemas/                     # Pydantic models for each SharePoint list (columns)
    file_triage.py               # triage_file: parse, classify, extract, triage
    components.py                # Agent-based pipeline components
    mappers.py                   # Triage models <-> SharePoint list fields
  receiver/                      # This application's webhook handlers (framework: gds_idea_sharepoint.receiver)
    route_handlers.py            # Business handlers (triage, QA, action extraction)
    lambda_handler.py            # AWS Lambda entry point (Mangum)
tests/
  unit/
    triage/                      # unit tests for triage module
    pipeline/                    # unit tests for pipeline mappers
    receiver/                    # unit tests for the QA and review handlers
  integration/
    triage/                      # LLM integration tests (deterministic)
  evals/
    triage/                      # LLM output quality evals (TODO: proper eval framework)
examples/
  triage/                        # triage example scripts
  data/                          # sample data for examples
```
