"""Skip all receiver tests when the receiver optional dependencies are not installed.

The receiver module depends on FastAPI which is an optional extra.
When running ``uv sync`` without ``--extra receiver``, these tests are
automatically skipped rather than failing with ImportError.
"""

import pytest

pytest.importorskip("fastapi", reason="receiver extras not installed (install with: uv sync --extra receiver)")
