"""
Tests for the SQLite-backed community board database.

These tests verify that:
- Entries can be submitted and retrieved
- Voting updates counts correctly and returns scores
- Voting on a nonexistent entry returns None
- The max entries cap prunes oldest entries
- Oversized images are rejected
- Legacy JSON data is migrated on first run
- Top entries are ranked by score (upvotes - downvotes)
"""

import json

import pytest

from community_db import CommunityDB, MAX_ENTRIES, MAX_IMAGE_SIZE


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Create a CommunityDB backed by a temp database, with migration disabled."""
    import community_db
    # Point LEGACY_JSON to a nonexistent path so migration doesn't import real data
    monkeypatch.setattr(community_db, "LEGACY_JSON", tmp_path / "nonexistent.json")
    return CommunityDB(db_path=str(tmp_path / "test_community.db"))


def _submit_entry(db, phrase="spider in blender", image_size=100):
    """Helper: submit a minimal entry and return the result."""
    return db.submit(
        phrase=phrase,
        intro="Spidey got blended.",
        caption="I threw him in the blender.",
        hashtags="#blender #spider death",
        image_base64="x" * image_size,
    )


class TestSubmitAndRetrieve:
    def test_submit_returns_id_and_timestamp(self, db):
        result = _submit_entry(db)
        assert "id" in result
        assert "created_at" in result
        assert len(result["id"]) == 36  # UUID format

    def test_submitted_entry_appears_in_top_entries(self, db):
        _submit_entry(db, phrase="spider in toaster")
        entries = db.top_entries()

        assert len(entries) == 1
        assert entries[0]["phrase"] == "spider in toaster"
        assert entries[0]["upvotes"] == 0
        assert entries[0]["downvotes"] == 0
        assert entries[0]["score"] == 0

    def test_multiple_entries_all_retrievable(self, db):
        for i in range(5):
            _submit_entry(db, phrase=f"death #{i}")
        entries = db.top_entries(limit=10)
        assert len(entries) == 5


class TestVoting:
    def test_upvote_increments(self, db):
        result = _submit_entry(db)
        entry_id = result["id"]

        vote_result = db.vote(entry_id, "up")
        assert vote_result["upvotes"] == 1
        assert vote_result["downvotes"] == 0
        assert vote_result["score"] == 1

    def test_downvote_increments(self, db):
        result = _submit_entry(db)
        entry_id = result["id"]

        vote_result = db.vote(entry_id, "down")
        assert vote_result["upvotes"] == 0
        assert vote_result["downvotes"] == 1
        assert vote_result["score"] == -1

    def test_multiple_votes_accumulate(self, db):
        result = _submit_entry(db)
        entry_id = result["id"]

        for _ in range(3):
            db.vote(entry_id, "up")
        db.vote(entry_id, "down")

        vote_result = db.vote(entry_id, "up")
        assert vote_result["upvotes"] == 4
        assert vote_result["downvotes"] == 1
        assert vote_result["score"] == 3

    def test_vote_on_nonexistent_entry_returns_none(self, db):
        result = db.vote("nonexistent-id-12345", "up")
        assert result is None

    def test_invalid_vote_direction_raises(self, db):
        """Passing anything other than 'up' or 'down' should raise ValueError."""
        result = _submit_entry(db)
        with pytest.raises(ValueError, match="Invalid vote direction"):
            db.vote(result["id"], "sideways")

    def test_top_entries_ranked_by_score(self, db):
        """Entries should be sorted by (upvotes - downvotes) descending."""
        r1 = _submit_entry(db, phrase="low scorer")
        r2 = _submit_entry(db, phrase="high scorer")
        r3 = _submit_entry(db, phrase="medium scorer")

        db.vote(r2["id"], "up")
        db.vote(r2["id"], "up")
        db.vote(r2["id"], "up")

        db.vote(r3["id"], "up")

        db.vote(r1["id"], "down")

        entries = db.top_entries()
        phrases = [e["phrase"] for e in entries]
        assert phrases == ["high scorer", "medium scorer", "low scorer"]


class TestImageSizeLimit:
    def test_rejects_oversized_image(self, db):
        with pytest.raises(ValueError, match="Image too large"):
            _submit_entry(db, image_size=MAX_IMAGE_SIZE + 1)

    def test_accepts_image_at_limit(self, db):
        result = _submit_entry(db, image_size=MAX_IMAGE_SIZE)
        assert "id" in result

    def test_accepts_small_image(self, db):
        result = _submit_entry(db, image_size=100)
        assert "id" in result


class TestEntryCap:
    def test_prunes_oldest_beyond_cap(self, db, monkeypatch):
        """When more than MAX_ENTRIES are submitted, the oldest should be pruned."""
        from datetime import datetime as real_datetime
        # Use a small cap for testing
        monkeypatch.setattr("community_db.MAX_ENTRIES", 5)

        # Deterministic timestamps so ordering is guaranteed without sleeps
        call_count = 0
        base = real_datetime(2026, 1, 1)
        def _advancing_now():
            nonlocal call_count
            call_count += 1
            return base.replace(second=call_count)
        monkeypatch.setattr("community_db.datetime", type("FakeDatetime", (), {
            "now": staticmethod(_advancing_now),
        }))

        ids = []
        for i in range(7):
            result = db.submit(
                phrase=f"entry {i}",
                intro=f"intro {i}",
                caption=f"caption {i}",
                hashtags=f"#tag{i}",
                image_base64="small",
            )
            ids.append(result["id"])

        entries = db.top_entries(limit=100)
        assert len(entries) == 5
        # The oldest entries (0 and 1) should have been pruned
        remaining_ids = {e["id"] for e in entries}
        assert ids[0] not in remaining_ids
        assert ids[1] not in remaining_ids
        # The newest entries should remain
        assert ids[6] in remaining_ids
        assert ids[5] in remaining_ids


class TestJsonMigration:
    def test_migrates_legacy_json_on_first_run(self, tmp_path, monkeypatch):
        """If community_board.json exists, its entries should be imported."""
        import community_db

        legacy_data = [
            {
                "id": "legacy-001",
                "phrase": "spider in microwave",
                "intro": "Spidey got zapped.",
                "caption": "I microwaved him.",
                "hashtags": "#microwave",
                "image_base64": "abc123",
                "upvotes": 5,
                "downvotes": 1,
                "created_at": "2026-01-01T00:00:00",
            }
        ]

        legacy_path = tmp_path / "community_board.json"
        with open(legacy_path, "w") as f:
            json.dump(legacy_data, f)

        monkeypatch.setattr(community_db, "LEGACY_JSON", legacy_path)
        db = CommunityDB(db_path=str(tmp_path / "test_migrate.db"))
        entries = db.top_entries()
        assert len(entries) == 1
        assert entries[0]["id"] == "legacy-001"
        assert entries[0]["phrase"] == "spider in microwave"
        assert entries[0]["upvotes"] == 5
        assert entries[0]["downvotes"] == 1

    def test_does_not_re_migrate_if_db_has_entries(self, tmp_path, monkeypatch):
        """Migration should only happen when the DB is empty."""
        import community_db

        legacy_data = [
            {
                "id": "legacy-001",
                "phrase": "should not appear",
                "intro": "x",
                "caption": "x",
                "hashtags": "x",
                "image_base64": "x",
                "upvotes": 0,
                "downvotes": 0,
                "created_at": "2026-01-01T00:00:00",
            }
        ]

        legacy_path = tmp_path / "community_board.json"
        with open(legacy_path, "w") as f:
            json.dump(legacy_data, f)

        db_path = str(tmp_path / "test_no_remigrate.db")

        monkeypatch.setattr(community_db, "LEGACY_JSON", legacy_path)

        # First init — should migrate
        db1 = CommunityDB(db_path=db_path)
        assert len(db1.top_entries()) == 1

        # Add another entry directly
        db1.submit(
            phrase="new entry",
            intro="x", caption="x", hashtags="x", image_base64="x",
        )
        assert len(db1.top_entries()) == 2

        # Second init — should NOT re-migrate (DB already has entries)
        db2 = CommunityDB(db_path=db_path)
        assert len(db2.top_entries()) == 2  # not 3
