"""Tests for src/outlook/auth.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# test_is_authenticated_no_file
# ---------------------------------------------------------------------------


def test_is_authenticated_no_file(tmp_path, monkeypatch):
    """Returns False when the token file does not exist."""
    monkeypatch.setenv("AZURE_CLIENT_ID", "fake-client-id")
    # Reload the module so AZURE_CLIENT_ID is picked up.
    import importlib
    import src.outlook.auth as auth_mod
    monkeypatch.setattr(auth_mod, "AZURE_CLIENT_ID", "fake-client-id")

    missing_path = tmp_path / "nonexistent_token.json"
    assert not missing_path.exists()
    result = auth_mod.is_authenticated(token_path=missing_path)
    assert result is False


# ---------------------------------------------------------------------------
# test_is_authenticated_no_client_id
# ---------------------------------------------------------------------------


def test_is_authenticated_no_client_id(tmp_path, monkeypatch):
    """Returns False when AZURE_CLIENT_ID is empty."""
    import src.outlook.auth as auth_mod
    # Patch the module-level constant directly.
    monkeypatch.setattr(auth_mod, "AZURE_CLIENT_ID", "")

    # Even if a token file exists, the check should short-circuit.
    token_path = tmp_path / "outlook_token.json"
    token_path.write_text("{}", encoding="utf-8")

    result = auth_mod.is_authenticated(token_path=token_path)
    assert result is False


# ---------------------------------------------------------------------------
# test_restrict_token_file_runs
# ---------------------------------------------------------------------------


def test_restrict_token_file_runs(tmp_path):
    """Smoke test: _restrict_token_file does not raise on a real file."""
    from src.outlook.auth import _restrict_token_file

    token_file = tmp_path / "test_token.json"
    token_file.write_text('{"test": true}', encoding="utf-8")

    # Should complete without raising any exception.
    _restrict_token_file(token_file)
    # File should still exist and be readable.
    assert token_file.exists()
    assert token_file.read_text(encoding="utf-8") == '{"test": true}'
