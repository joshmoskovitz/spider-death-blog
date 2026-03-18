#!/usr/bin/env python3
"""
Spider Death Blog — Community Board Database

SQLite-backed storage for user-generated spider death submissions.
Replaces the previous community_board.json approach, which had race
conditions under concurrent writes and no size limits.

Auto-migrates existing JSON data on first run.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / "community.db"
LEGACY_JSON = PROJECT_DIR / "community_board.json"

MAX_ENTRIES = 200
MAX_IMAGE_SIZE = 500_000  # 500 KB base64 limit


class CommunityDB:
    """SQLite-backed community board with auto-migration and size caps."""

    def __init__(self, db_path: str = str(DB_PATH)):
        self._db_path = db_path
        self._init_db()
        self._maybe_migrate_json()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS entries ("
                "  id TEXT PRIMARY KEY,"
                "  phrase TEXT NOT NULL,"
                "  intro TEXT NOT NULL,"
                "  caption TEXT NOT NULL,"
                "  hashtags TEXT NOT NULL,"
                "  image_base64 TEXT NOT NULL,"
                "  upvotes INTEGER NOT NULL DEFAULT 0,"
                "  downvotes INTEGER NOT NULL DEFAULT 0,"
                "  created_at TEXT NOT NULL"
                ")"
            )

    def _connect(self):
        return sqlite3.connect(self._db_path)

    def _maybe_migrate_json(self):
        """One-time migration from community_board.json if it exists."""
        if not LEGACY_JSON.exists():
            return
        # Only migrate if the DB is empty
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            if count > 0:
                return

        with open(LEGACY_JSON) as f:
            entries = json.load(f)

        with self._connect() as conn:
            for entry in entries:
                conn.execute(
                    "INSERT OR IGNORE INTO entries "
                    "(id, phrase, intro, caption, hashtags, image_base64, "
                    "upvotes, downvotes, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        entry.get("id", str(uuid.uuid4())),
                        entry.get("phrase", ""),
                        entry.get("intro", ""),
                        entry.get("caption", ""),
                        entry.get("hashtags", ""),
                        entry.get("image_base64", ""),
                        entry.get("upvotes", 0),
                        entry.get("downvotes", 0),
                        entry.get("created_at", datetime.now().isoformat()),
                    ),
                )

    def submit(self, phrase: str, intro: str, caption: str,
               hashtags: str, image_base64: str) -> dict:
        """Add a new entry. Prunes oldest entries if at capacity."""
        if len(image_base64) > MAX_IMAGE_SIZE:
            raise ValueError(
                f"Image too large ({len(image_base64)} bytes). "
                f"Maximum is {MAX_IMAGE_SIZE} bytes."
            )

        entry_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()

        with self._connect() as conn:
            conn.execute(
                "INSERT INTO entries "
                "(id, phrase, intro, caption, hashtags, image_base64, "
                "upvotes, downvotes, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)",
                (entry_id, phrase, intro, caption, hashtags,
                 image_base64, created_at),
            )
            # Prune oldest entries beyond the cap
            conn.execute(
                "DELETE FROM entries WHERE id NOT IN ("
                "  SELECT id FROM entries ORDER BY created_at DESC LIMIT ?"
                ")",
                (MAX_ENTRIES,),
            )

        return {"id": entry_id, "created_at": created_at}

    def top_entries(self, limit: int = 20) -> List[dict]:
        """Return the top entries ranked by score (upvotes - downvotes)."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT *, (upvotes - downvotes) AS score FROM entries "
                "ORDER BY score DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def vote(self, entry_id: str, direction: str) -> Optional[dict]:
        """Vote on an entry. Returns updated vote counts or None if not found."""
        if direction not in ("up", "down"):
            raise ValueError(f"Invalid vote direction: {direction!r} (expected 'up' or 'down')")
        # Use separate SQL statements rather than f-string interpolation to
        # avoid any coupling between the validation above and SQL safety.
        if direction == "up":
            sql = "UPDATE entries SET upvotes = upvotes + 1 WHERE id = ?"
        else:
            sql = "UPDATE entries SET downvotes = downvotes + 1 WHERE id = ?"
        with self._connect() as conn:
            conn.execute(sql, (entry_id,))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT upvotes, downvotes FROM entries WHERE id = ?",
                (entry_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "upvotes": row["upvotes"],
                "downvotes": row["downvotes"],
                "score": row["upvotes"] - row["downvotes"],
            }
