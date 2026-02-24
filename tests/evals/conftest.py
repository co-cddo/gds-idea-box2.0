"""
Pytest configuration for LLM output quality evals.

Evals require AWS credentials (same as integration tests) but are excluded
from default test runs. Run explicitly with: uv run pytest -m eval -v

Evals use fuzzy matching and semantic heuristics to assess LLM output quality.
Some failure is expected -- these measure quality, not correctness.
"""

import os

import pytest


def _has_aws_credentials() -> bool:
    """Check if AWS credentials are available for evals."""
    if os.environ.get("AWS_PROFILE"):
        return True
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return True
    return False


def pytest_collection_modifyitems(config, items):
    """Auto-skip evals when AWS credentials are not available."""
    if _has_aws_credentials():
        return

    skip_eval = pytest.mark.skip(reason="AWS credentials not available (set AWS_PROFILE or AWS_ACCESS_KEY_ID)")
    for item in items:
        if "eval" in item.keywords:
            item.add_marker(skip_eval)
