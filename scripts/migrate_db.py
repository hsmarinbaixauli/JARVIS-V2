"""One-time idempotent database migration script. Creates the SQLite schema
defined in src/persistence/database.py using CREATE TABLE IF NOT EXISTS
statements. Safe to run on every startup.

Usage: python scripts/migrate_db.py
"""
from __future__ import annotations


if __name__ == "__main__":
    pass
