"""Microsoft Graph / MSAL authentication for Outlook.

Device-code flow for initial sign-in; token cache persisted to
credentials/outlook_token.json. Subsequent calls use silent refresh.

Public API:
    is_authenticated() -> bool
    get_outlook_token() -> str
    start_device_code_flow() -> dict
    complete_device_code_flow(flow: dict) -> bool
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import msal

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCOPES = ["Mail.Read", "Mail.Send", "User.Read", "offline_access"]
_TENANT_ID = "2cb0ae1d-fc5b-4c31-a900-9fda54a1e85d"
_AUTHORITY = f"https://login.microsoftonline.com/{_TENANT_ID}"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TOKEN_PATH = _PROJECT_ROOT / "credentials" / "outlook_token.json"

AZURE_CLIENT_ID: str = os.environ.get("AZURE_CLIENT_ID", "")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_authenticated(token_path: Path = _TOKEN_PATH) -> bool:
    """Return True if a valid cached token exists for the configured client.

    Performs no network call — only checks the local token cache file.
    Returns False immediately if AZURE_CLIENT_ID is not set or the token
    file does not exist.
    """
    if not AZURE_CLIENT_ID:
        return False
    if not token_path.exists():
        return False
    try:
        cache = _load_cache(token_path)
        app = _build_msal_app(cache)
        accounts = app.get_accounts()
        return len(accounts) > 0
    except Exception as exc:  # noqa: BLE001
        _log.warning("is_authenticated check failed: %s", exc)
        return False


def get_outlook_token(token_path: Path = _TOKEN_PATH) -> str:
    """Return a valid access token for Microsoft Graph.

    Raises:
        RuntimeError: If AZURE_CLIENT_ID is not set, or if silent token
            acquisition fails (token expired and cannot be refreshed).
    """
    if not AZURE_CLIENT_ID:
        raise RuntimeError("AZURE_CLIENT_ID not set")
    cache = _load_cache(token_path)
    app = _build_msal_app(cache)
    accounts = app.get_accounts()
    if not accounts:
        raise RuntimeError("No cached account found. Run device-code flow first.")
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result and "access_token" in result:
        # Persist any refreshed tokens back to disk.
        if cache.has_state_changed:
            _save_cache(cache, token_path)
        return result["access_token"]
    raise RuntimeError(result.get("error_description", "Token acquisition failed") if result else "Token acquisition failed")


def start_device_code_flow() -> dict:
    """Initiate the MSAL device-code flow.

    Returns the flow dict as-is from MSAL, which includes:
        verification_uri, user_code, expires_in, message.

    Raises:
        RuntimeError: If AZURE_CLIENT_ID is not set.
    """
    if not AZURE_CLIENT_ID:
        raise RuntimeError("AZURE_CLIENT_ID not set")
    app = _build_msal_app()
    flow = app.initiate_device_flow(scopes=SCOPES)
    return flow


def complete_device_code_flow(flow: dict, token_path: Path = _TOKEN_PATH) -> bool:
    """Block until the user completes the device-code flow or it times out.

    MSAL polls Azure internally while this call blocks.

    Args:
        flow: The flow dict returned by start_device_code_flow().
        token_path: Where to persist the token cache on success.

    Returns:
        True on success, False on failure or timeout.
    """
    cache = msal.SerializableTokenCache()
    app = _build_msal_app(cache)
    result = app.acquire_token_by_device_flow(flow)
    if result and "access_token" in result:
        _save_cache(cache, token_path)
        return True
    error = result.get("error_description", result.get("error", "unknown")) if result else "unknown"
    _log.error("Device-code flow failed: %s", error)
    return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_msal_app(cache: msal.SerializableTokenCache | None = None) -> msal.PublicClientApplication:
    """Build a PublicClientApplication, optionally backed by *cache*."""
    return msal.PublicClientApplication(
        AZURE_CLIENT_ID,
        authority=_AUTHORITY,
        token_cache=cache,
    )


def _load_cache(path: Path) -> msal.SerializableTokenCache:
    """Load a serialised token cache from *path*, or return an empty cache."""
    cache = msal.SerializableTokenCache()
    if path.exists():
        try:
            cache.deserialize(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            _log.warning("Could not deserialise token cache at %s: %s", path, exc)
    return cache


def _save_cache(cache: msal.SerializableTokenCache, path: Path = _TOKEN_PATH) -> None:
    """Persist *cache* to *path* and restrict file permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cache.serialize(), encoding="utf-8")
    _restrict_token_file(path)


def _restrict_token_file(path: Path) -> None:
    """Restrict *path* so only the current user can read it.

    On Windows uses ``icacls`` to remove inherited ACEs and grant the current
    user read-only access.  On other platforms falls back to ``chmod 600``.
    """
    if sys.platform == "win32":
        username: str | None = os.getenv("USERNAME")
        if not username:
            _log.warning("Could not determine USERNAME; token file ACL not restricted: %s", path)
            return
        try:
            result = subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{username}:(F)"],
                check=False,
                capture_output=True,
            )
            if result.returncode != 0:
                _log.warning(
                    "icacls exited with %d for %s: %s",
                    result.returncode, path,
                    result.stderr.decode(errors="replace"),
                )
        except Exception as exc:  # noqa: BLE001
            _log.warning("icacls failed to restrict token file %s: %s", path, exc)
    else:
        os.chmod(path, 0o600)
