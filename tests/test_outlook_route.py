"""Tests for src/api/routes/outlook.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture()
def client():
    app = create_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# test_auth_status_unauthenticated
# ---------------------------------------------------------------------------


def test_auth_status_unauthenticated(client):
    """GET /api/outlook/auth-status returns {authenticated: false} when not authed."""
    with patch("src.outlook.auth.is_authenticated", return_value=False):
        response = client.get("/api/outlook/auth-status")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


# ---------------------------------------------------------------------------
# test_summary_unauthenticated_returns_demo
# ---------------------------------------------------------------------------


def test_summary_unauthenticated_returns_demo(client):
    """GET /api/outlook/summary returns 200 with DEMO content when not authenticated."""
    with patch("src.outlook.auth.is_authenticated", return_value=False):
        response = client.get("/api/outlook/summary")
    assert response.status_code == 200
    data = response.json()
    assert "resumen_general" in data
    assert "DEMO" in data["resumen_general"]
