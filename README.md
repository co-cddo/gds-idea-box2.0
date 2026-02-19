# Box 2.0

AI tools for private office workflows. Currently includes a **triage** module that processes ministerial correspondence — classifying documents, extracting structured data, triaging decisions, and drafting responses — and a **sharepoint** module for authenticated access to SharePoint via Microsoft Graph API.

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
  integration/    # calls live LLM via AWS Bedrock / SharePoint via Graph API
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
AWS_PROFILE=bedrock-dev uv run python examples/triage/email_end_to_end.py
AWS_PROFILE=bedrock-dev uv run python examples/triage/triage.py
uv run python examples/sharepoint/auth.py
uv run python examples/sharepoint/list_operations.py
```

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
    exceptions.py                # SharePoint exception hierarchy
tests/
  unit/
    triage/                      # unit tests for triage module
    sharepoint/                  # unit tests for SharePoint module
  integration/
    triage/                      # LLM integration tests
    sharepoint/                  # SharePoint integration tests
examples/
  triage/                        # triage example scripts
  sharepoint/                    # SharePoint example scripts
  data/                          # sample data for examples
```
