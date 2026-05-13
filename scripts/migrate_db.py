"""Idempotent database migration script.

Creates the SQLite schema using CREATE TABLE IF NOT EXISTS.
Safe to run on every startup or manually.

Usage:
    python scripts/migrate_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when run as a standalone script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

from src.persistence.database import _DB_PATH, init_db  # noqa: E402

if __name__ == "__main__":
    print(f"Initializing database at: {_DB_PATH}")
    init_db()
    print("Done.")
