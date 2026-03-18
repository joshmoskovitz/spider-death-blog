"""
Tests for the daily autonomous pipeline.

These tests verify the archiving logic and budget checking without
calling the Anthropic API. The generate/improve/build steps are not
tested here because they require API access — they are integration
tests best run with a real (or mocked) API key.

Specifically, these tests ensure that:
- archive_post correctly appends to posts.json and copies the image
- archive_post handles missing images gracefully
- check_budget aborts at 90% of daily limit
- check_budget aborts at 90% of monthly limit
- check_budget passes when under budget
- log_event writes structured JSONL entries
"""

import json
import os
import time
from pathlib import Path

import pytest

import costs
import daily_pipeline


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path, monkeypatch):
    """Redirect all file paths to temp directories."""
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    images_dir = archive_dir / "images"
    images_dir.mkdir()
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir()

    # Seed with a minimal archive
    archive_path = archive_dir / "posts.json"
    with open(archive_path, "w") as f:
        json.dump([{"setting": "original post", "mechanism": "original"}], f)

    monkeypatch.setattr(daily_pipeline, "ARCHIVE_PATH", archive_path)
    monkeypatch.setattr(daily_pipeline, "ARCHIVE_IMAGES", images_dir)
    monkeypatch.setattr(daily_pipeline, "DRAFTS_DIR", drafts_dir)
    monkeypatch.setattr(daily_pipeline, "LOG_PATH", tmp_path / "test_log.jsonl")

    # Also redirect costs log so budget checks use a clean file
    monkeypatch.setattr(costs, "COSTS_LOG", tmp_path / "costs.jsonl")

    return tmp_path


@pytest.fixture(autouse=True)
def clear_budget_env(monkeypatch):
    monkeypatch.delenv("DAILY_BUDGET", raising=False)
    monkeypatch.delenv("MONTHLY_BUDGET", raising=False)


# ---------------------------------------------------------------------------
# archive_post
# ---------------------------------------------------------------------------

class TestArchivePost:
    def _make_draft(self, tmp_path, setting="laundromat"):
        """Create a fake draft batch with an image file."""
        drafts_dir = tmp_path / "drafts"
        post_data = {
            "setting": setting,
            "mechanism": "spin cycle",
            "main_prop": "washing machine",
            "intro": "Spidey's getting cleaned up.",
            "caption": "I tossed him in with the darks.",
            "hashtags": "#laundry #spider death",
            "hidden_touch": "a tiny sock",
            "scene_description": "a laundromat scene",
        }
        batch_path = drafts_dir / "batch_test.json"
        with open(batch_path, "w") as f:
            json.dump([post_data], f)

        # Create a fake image
        setting_slug = setting.replace(" ", "_")
        image_path = drafts_dir / f"draft_1_{setting_slug}.png"
        image_path.write_bytes(b"fake png data")

        return str(batch_path), post_data

    def test_appends_entry_to_archive(self, isolated_paths):
        batch_path, post_data = self._make_draft(isolated_paths)

        post_id = daily_pipeline.archive_post(batch_path, post_data)

        assert post_id == 2  # second post (one already in archive)

        with open(daily_pipeline.ARCHIVE_PATH) as f:
            archive = json.load(f)
        assert len(archive) == 2
        assert archive[1]["setting"] == "laundromat"
        assert archive[1]["mechanism"] == "spin cycle"
        assert archive[1]["date"] is not None

    def test_copies_image_to_archive(self, isolated_paths):
        batch_path, post_data = self._make_draft(isolated_paths)

        daily_pipeline.archive_post(batch_path, post_data)

        # Check the image was copied
        expected_image = daily_pipeline.ARCHIVE_IMAGES / "02_laundromat.png"
        assert expected_image.exists()
        assert expected_image.read_bytes() == b"fake png data"

    def test_handles_missing_image_gracefully(self, isolated_paths):
        """If the draft image doesn't exist, archiving should still succeed."""
        drafts_dir = isolated_paths / "drafts"
        post_data = {
            "setting": "the void",
            "mechanism": "nothingness",
        }
        batch_path = drafts_dir / "batch_test.json"
        with open(batch_path, "w") as f:
            json.dump([post_data], f)

        # No image file created — should not raise
        post_id = daily_pipeline.archive_post(str(batch_path), post_data)
        assert post_id == 2

    def test_increments_post_id_correctly(self, isolated_paths):
        """Each archived post should get the next sequential ID."""
        batch_path, post_data = self._make_draft(isolated_paths, "gym")
        daily_pipeline.archive_post(batch_path, post_data)

        batch_path2, post_data2 = self._make_draft(isolated_paths, "library")
        post_id = daily_pipeline.archive_post(batch_path2, post_data2)

        assert post_id == 3  # third post total


# ---------------------------------------------------------------------------
# check_budget
# ---------------------------------------------------------------------------

class TestCheckBudget:
    def test_passes_when_no_limits_set(self):
        daily_pipeline.check_budget()  # should not raise

    def test_passes_when_under_daily_limit(self, isolated_paths, monkeypatch):
        monkeypatch.setenv("DAILY_BUDGET", "10.00")
        now = time.time()
        # Spend $1 today — well under 90% of $10
        log_path = isolated_paths / "costs.jsonl"
        entry = {"timestamp": now - 10, "cost_usd": 1.00}
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        daily_pipeline.check_budget()  # should not raise

    def test_aborts_at_90_percent_of_daily_limit(self, isolated_paths, monkeypatch):
        monkeypatch.setenv("DAILY_BUDGET", "10.00")
        now = time.time()
        # Spend $9.50 today — over 90% threshold
        log_path = isolated_paths / "costs.jsonl"
        entry = {"timestamp": now - 10, "cost_usd": 9.50}
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        with pytest.raises(RuntimeError, match="Near daily budget"):
            daily_pipeline.check_budget()

    def test_aborts_at_90_percent_of_monthly_limit(self, isolated_paths, monkeypatch):
        monkeypatch.setenv("MONTHLY_BUDGET", "50.00")
        now = time.time()
        log_path = isolated_paths / "costs.jsonl"
        entry = {"timestamp": now - 10, "cost_usd": 46.00}
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        with pytest.raises(RuntimeError, match="Near monthly budget"):
            daily_pipeline.check_budget()


# ---------------------------------------------------------------------------
# log_event
# ---------------------------------------------------------------------------

class TestLogEvent:
    def test_writes_structured_entry(self, isolated_paths):
        daily_pipeline.log_event("test_event", message="hello", extra="data")

        log_path = daily_pipeline.LOG_PATH
        with open(log_path) as f:
            entry = json.loads(f.readline())
        assert entry["event"] == "test_event"
        assert entry["message"] == "hello"
        assert entry["extra"] == "data"
        assert "timestamp" in entry

    def test_multiple_events_accumulate(self, isolated_paths):
        daily_pipeline.log_event("event1", message="first")
        daily_pipeline.log_event("event2", message="second")

        with open(daily_pipeline.LOG_PATH) as f:
            lines = f.readlines()
        assert len(lines) == 2
