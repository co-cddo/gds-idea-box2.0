"""Tests for the SharePoint list-schema package and its relationship to the triage models."""

import ast
from pathlib import Path

import pytest

import box2
from box2.pipeline import schemas
from box2.triage.models.invitation import EventType

SRC = Path(box2.__file__).parent


# ===== Public API =====


@pytest.mark.parametrize(
    "name",
    ["SharepointAction", "SharepointInvitation", "SharepointInvitationQA", "SharepointPQs", "SharepointSubmission"],
)
def test_schema_models_exported(name):
    """Each list-schema model is importable from box2.pipeline.schemas."""
    assert name in schemas.__all__
    assert hasattr(schemas, name)


def test_invitation_schema_shares_the_domain_event_type():
    """The invitation list schema uses the triage EventType rather than a duplicate enum."""
    assert schemas.SharepointInvitation.model_fields["event_type"].annotation is EventType


def test_invitation_qa_is_an_invitation_schema():
    """The QA list schema extends the invitation schema, so they share one EventType."""
    assert issubclass(schemas.SharepointInvitationQA, schemas.SharepointInvitation)


# ===== Dependency direction =====


def _box2_imports(package: str) -> set[str]:
    """Return the box2 subpackages imported anywhere under ``src/box2/<package>``."""
    found: set[str] = set()
    for path in (SRC / package).rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]
            for module in modules:
                parts = module.split(".")
                if parts[0] == "box2" and len(parts) > 1:
                    found.add(parts[1])
    return found


def test_triage_does_not_depend_on_pipeline_or_receiver():
    """triage is the LLM/domain core and must not import the layers built on top of it."""
    assert _box2_imports("triage") <= {"triage"}


def test_pipeline_does_not_depend_on_receiver():
    """pipeline may use triage but never the receiver, which sits above it."""
    assert _box2_imports("pipeline") <= {"pipeline", "triage"}
