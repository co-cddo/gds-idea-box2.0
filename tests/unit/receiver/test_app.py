"""Unit tests for the FastAPI webhook receiver routes.

Uses FastAPI's TestClient (backed by httpx) to test the full HTTP contract
without a running server.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from box2.receiver.app import create_app
from box2.receiver.config import ReceiverConfig
from box2.receiver.dedup import InMemoryDedup

# ============================================================================
# Fixtures
# ============================================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures"
CLIENT_STATE = "test-secret"

VALID_NOTIFICATION = {
    "subscriptionId": "sub-abc-123",
    "changeType": "created",
    "clientState": CLIENT_STATE,
    "resource": "sites/site-id/lists/list-id/items/42",
    "tenantId": "tenant-id-999",
}


@pytest.fixture
def config():
    """Create a ReceiverConfig for testing."""
    return ReceiverConfig(client_state=CLIENT_STATE)


@pytest.fixture
def app(config):
    """Create a FastAPI test app with a fresh dedup store."""
    store = InMemoryDedup(window_seconds=300)
    return create_app(config, dedup_store=store)


@pytest.fixture
def client(app):
    """Create a FastAPI TestClient."""
    from starlette.testclient import TestClient

    return TestClient(app)


# ============================================================================
# Validation Handshake Tests
# ============================================================================


def test_validation_handshake_echoes_token(client):
    """POST /webhook with validationToken should echo the token back."""
    response = client.post("/webhook?validationToken=abc-token-123")

    assert response.status_code == 200
    assert response.text == "abc-token-123"


def test_validation_handshake_returns_plain_text(client):
    """Validation response should have text/plain content type."""
    response = client.post("/webhook?validationToken=abc-token-123")

    assert "text/plain" in response.headers["content-type"]


def test_validation_handshake_with_special_characters(client):
    """Validation token with URL-encoded characters should be echoed correctly."""
    response = client.post("/webhook?validationToken=token%20with%20spaces")

    assert response.status_code == 200
    assert response.text == "token with spaces"


# ============================================================================
# Notification Processing Tests
# ============================================================================


@patch("box2.receiver.handlers.dispatch")
def test_notification_returns_202(mock_dispatch, client):
    """POST /webhook with a valid notification payload should return 202."""
    response = client.post("/webhook", json={"value": [VALID_NOTIFICATION]})

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


@patch("box2.receiver.handlers.dispatch")
def test_notification_dispatches_valid_notification(mock_dispatch, client):
    """A valid notification should be dispatched to the handler."""
    client.post("/webhook", json={"value": [VALID_NOTIFICATION]})

    mock_dispatch.assert_called_once()


@patch("box2.receiver.handlers.dispatch")
def test_notification_wrong_client_state_still_returns_202(mock_dispatch, client):
    """Notifications with wrong clientState should still return 202 (accepted but skipped)."""
    bad = {**VALID_NOTIFICATION, "clientState": "wrong-secret"}
    response = client.post("/webhook", json={"value": [bad]})

    assert response.status_code == 202
    mock_dispatch.assert_not_called()


@patch("box2.receiver.handlers.dispatch")
def test_duplicate_notification_not_dispatched_twice(mock_dispatch, client):
    """Sending the same notification twice should only dispatch once."""
    payload = {"value": [VALID_NOTIFICATION]}

    client.post("/webhook", json=payload)
    client.post("/webhook", json=payload)

    mock_dispatch.assert_called_once()


@patch("box2.receiver.handlers.dispatch")
def test_fixture_file_notification(mock_dispatch, client):
    """The list_item_created fixture should be accepted and dispatched."""
    fixture_path = FIXTURES_DIR / "list_item_created.json"
    with open(fixture_path) as f:
        data = json.load(f)

    response = client.post("/webhook", json=data)

    assert response.status_code == 202
    mock_dispatch.assert_called_once()


# ============================================================================
# Health Endpoint Tests
# ============================================================================


def test_health_returns_200(client):
    """GET /health should return 200."""
    response = client.get("/health")

    assert response.status_code == 200


def test_health_returns_ok_status(client):
    """GET /health should return {"status": "ok"}."""
    response = client.get("/health")

    assert response.json() == {"status": "ok"}


# ============================================================================
# Config Validation Tests
# ============================================================================


def test_config_requires_client_state():
    """ReceiverConfig should reject an empty client_state."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ReceiverConfig(client_state="")


def test_config_requires_positive_dedup_window():
    """ReceiverConfig should reject a non-positive dedup_window_seconds."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ReceiverConfig(client_state="secret", dedup_window_seconds=0)
