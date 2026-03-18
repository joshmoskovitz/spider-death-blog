#!/usr/bin/env python3
"""
Spider Death Blog — Persistent Rate Limiter

SQLite-backed rate limiting that survives server restarts.
Each request is logged with its IP and timestamp, and old entries
are pruned automatically.
"""

import sqlite3
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / "rate_limits.db"


class RateLimiter:
    """Per-IP rate limiter backed by a SQLite database."""

    def __init__(self, db_path: str = str(DB_PATH)):
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS requests ("
                "  ip TEXT NOT NULL,"
                "  timestamp REAL NOT NULL"
                ")"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_requests_ip_ts "
                "ON requests (ip, timestamp)"
            )

    def _connect(self):
        return sqlite3.connect(self._db_path)

    def is_rate_limited(self, ip: str, max_requests: int, window_seconds: int) -> bool:
        """Check if an IP has exceeded its request limit within the time window."""
        cutoff = time.time() - window_seconds
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM requests WHERE ip = ? AND timestamp > ?",
                (ip, cutoff),
            ).fetchone()
            return row[0] >= max_requests

    def record_request(self, ip: str):
        """Log a request from the given IP."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO requests (ip, timestamp) VALUES (?, ?)",
                (ip, time.time()),
            )

    def prune(self, max_age_seconds: int = 86400):
        """Delete entries older than max_age_seconds (default: 24 hours)."""
        cutoff = time.time() - max_age_seconds
        with self._connect() as conn:
            conn.execute("DELETE FROM requests WHERE timestamp < ?", (cutoff,))
