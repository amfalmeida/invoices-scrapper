from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone


class State:
    """Persists which invoices were already sent, plus small provider key/value data
    (e.g. rotating refresh tokens)."""

    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sent (
                key TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

    def is_sent(self, key: str) -> bool:
        return self._db.execute("SELECT 1 FROM sent WHERE key = ?", (key,)).fetchone() is not None

    def mark_sent(self, key: str) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO sent (key, sent_at) VALUES (?, ?)",
            (key, datetime.now(timezone.utc).isoformat()),
        )
        self._db.commit()

    def get(self, key: str, default=None):
        row = self._db.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key: str, value) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)", (key, json.dumps(value))
        )
        self._db.commit()
