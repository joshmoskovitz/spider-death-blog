"""
Tests for the persistent SQLite-backed rate limiter.

These tests verify that:
- Rate limiting correctly counts requests within a time window
- Different IPs are tracked independently
- Rate limit state persists across RateLimiter instances (simulating restarts)
- Old entries are pruned correctly
- The limiter works at exact boundaries (at the limit, one over, window edge)
"""

import time

import pytest

from rate_limiter import RateLimiter


@pytest.fixture
def limiter(tmp_path):
    """Create a RateLimiter backed by a temp database."""
    return RateLimiter(db_path=str(tmp_path / "test_rates.db"))


@pytest.fixture
def db_path(tmp_path):
    """Return the temp database path for persistence tests."""
    return str(tmp_path / "test_rates.db")


class TestRateLimiting:
    def test_not_limited_with_no_requests(self, limiter):
        assert limiter.is_rate_limited("1.2.3.4", max_requests=5, window_seconds=3600) is False

    def test_not_limited_under_threshold(self, limiter):
        for _ in range(4):
            limiter.record_request("1.2.3.4")
        assert limiter.is_rate_limited("1.2.3.4", max_requests=5, window_seconds=3600) is False

    def test_limited_at_threshold(self, limiter):
        for _ in range(5):
            limiter.record_request("1.2.3.4")
        assert limiter.is_rate_limited("1.2.3.4", max_requests=5, window_seconds=3600) is True

    def test_limited_over_threshold(self, limiter):
        for _ in range(10):
            limiter.record_request("1.2.3.4")
        assert limiter.is_rate_limited("1.2.3.4", max_requests=5, window_seconds=3600) is True

    def test_different_ips_tracked_independently(self, limiter):
        for _ in range(5):
            limiter.record_request("1.1.1.1")
        limiter.record_request("2.2.2.2")

        assert limiter.is_rate_limited("1.1.1.1", max_requests=5, window_seconds=3600) is True
        assert limiter.is_rate_limited("2.2.2.2", max_requests=5, window_seconds=3600) is False

    def test_old_requests_dont_count(self, limiter, monkeypatch):
        """Requests outside the time window should not count toward the limit."""
        # Record 5 requests "in the past" by using a tiny window
        for _ in range(5):
            limiter.record_request("1.2.3.4")

        # With a window of 0 seconds, all requests are "old"
        assert limiter.is_rate_limited("1.2.3.4", max_requests=5, window_seconds=0) is False


class TestPersistence:
    def test_state_survives_new_instance(self, db_path):
        """Rate limit state should persist when a new RateLimiter is created
        with the same database — simulating a server restart."""
        limiter1 = RateLimiter(db_path=db_path)
        for _ in range(5):
            limiter1.record_request("1.2.3.4")

        # Create a new instance (simulating restart)
        limiter2 = RateLimiter(db_path=db_path)
        assert limiter2.is_rate_limited("1.2.3.4", max_requests=5, window_seconds=3600) is True

    def test_empty_db_after_fresh_init(self, db_path):
        limiter = RateLimiter(db_path=db_path)
        assert limiter.is_rate_limited("1.2.3.4", max_requests=1, window_seconds=3600) is False


class TestPrune:
    def test_prune_removes_old_entries(self, limiter):
        for _ in range(5):
            limiter.record_request("1.2.3.4")

        # Prune everything older than 0 seconds (i.e., all entries)
        limiter.prune(max_age_seconds=0)

        assert limiter.is_rate_limited("1.2.3.4", max_requests=5, window_seconds=3600) is False

    def test_prune_keeps_recent_entries(self, limiter):
        for _ in range(5):
            limiter.record_request("1.2.3.4")

        # Prune entries older than 1 hour — recent entries should remain
        limiter.prune(max_age_seconds=3600)

        assert limiter.is_rate_limited("1.2.3.4", max_requests=5, window_seconds=3600) is True
