"""
Tests for the cost tracking and budget enforcement module.

These tests verify that:
- Cost estimation is correct for known and unknown models
- The cost log file records entries properly
- Budget enforcement blocks calls when limits are reached
- The reverse-scan optimization terminates early on old entries
- The TrackedMessages proxy passes through unwrapped methods
"""

import json
import os
import time
from unittest.mock import MagicMock

import pytest

import costs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_costs_log(tmp_path, monkeypatch):
    """Redirect the costs log to a temp file so tests don't pollute each other."""
    log_path = tmp_path / "costs.jsonl"
    monkeypatch.setattr(costs, "COSTS_LOG", log_path)
    return log_path


@pytest.fixture(autouse=True)
def clear_budget_env(monkeypatch):
    """Ensure no budget env vars leak between tests."""
    monkeypatch.delenv("DAILY_BUDGET", raising=False)
    monkeypatch.delenv("MONTHLY_BUDGET", raising=False)


def _write_cost_entry(log_path, timestamp, cost_usd, model="claude-sonnet-4-6"):
    """Helper: write a single cost entry to the log at a specific timestamp."""
    entry = {
        "timestamp": timestamp,
        "datetime": "2026-03-18T12:00:00+00:00",
        "model": model,
        "input_tokens": 1000,
        "output_tokens": 100,
        "cost_usd": cost_usd,
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

class TestEstimateCost:
    def test_known_model_sonnet(self):
        # 1000 input tokens at $3/M + 500 output tokens at $15/M
        cost = costs._estimate_cost("claude-sonnet-4-6", 1000, 500)
        expected = (1000 * 3.00 + 500 * 15.00) / 1_000_000
        assert cost == pytest.approx(expected)

    def test_known_model_haiku(self):
        cost = costs._estimate_cost("claude-haiku-4-5-20251001", 1000, 500)
        expected = (1000 * 0.80 + 500 * 4.00) / 1_000_000
        assert cost == pytest.approx(expected)

    def test_unknown_model_uses_fallback(self, capsys):
        cost = costs._estimate_cost("claude-mystery-99", 1000, 500)
        # Fallback uses the most expensive rate (same as Sonnet)
        expected = (1000 * 3.00 + 500 * 15.00) / 1_000_000
        assert cost == pytest.approx(expected)
        # Should print a warning to stderr
        captured = capsys.readouterr()
        assert "unknown model" in captured.err
        assert "claude-mystery-99" in captured.err

    def test_zero_tokens(self):
        assert costs._estimate_cost("claude-sonnet-4-6", 0, 0) == 0.0

    def test_large_token_count(self):
        # 1M input + 1M output
        cost = costs._estimate_cost("claude-sonnet-4-6", 1_000_000, 1_000_000)
        expected = 3.00 + 15.00  # exactly the per-million rates
        assert cost == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Log file loading
# ---------------------------------------------------------------------------

class TestLoadCostsSince:
    def test_empty_log_returns_zero(self, isolated_costs_log):
        assert costs._load_costs_since(0) == 0.0

    def test_missing_log_returns_zero(self, isolated_costs_log):
        # Don't create the file at all
        if isolated_costs_log.exists():
            isolated_costs_log.unlink()
        assert costs._load_costs_since(0) == 0.0

    def test_sums_entries_after_cutoff(self, isolated_costs_log):
        now = time.time()
        _write_cost_entry(isolated_costs_log, now - 100, 1.00)  # old
        _write_cost_entry(isolated_costs_log, now - 50, 2.00)   # recent
        _write_cost_entry(isolated_costs_log, now - 10, 3.00)   # recent

        total = costs._load_costs_since(now - 60)
        assert total == pytest.approx(5.00)

    def test_stops_at_older_entries(self, isolated_costs_log):
        """Verify the reverse-scan optimization terminates early."""
        now = time.time()
        # Write 100 old entries, then 2 recent ones
        for i in range(100):
            _write_cost_entry(isolated_costs_log, now - 10000 + i, 0.01)
        _write_cost_entry(isolated_costs_log, now - 5, 1.00)
        _write_cost_entry(isolated_costs_log, now - 1, 2.00)

        total = costs._load_costs_since(now - 10)
        assert total == pytest.approx(3.00)

    def test_handles_corrupt_lines(self, isolated_costs_log):
        now = time.time()
        _write_cost_entry(isolated_costs_log, now - 10, 1.00)
        # Write garbage
        with open(isolated_costs_log, "a") as f:
            f.write("this is not json\n")
        _write_cost_entry(isolated_costs_log, now - 5, 2.00)

        # Should skip the corrupt line and sum the valid ones
        total = costs._load_costs_since(now - 20)
        assert total == pytest.approx(3.00)

    def test_handles_blank_lines(self, isolated_costs_log):
        now = time.time()
        _write_cost_entry(isolated_costs_log, now - 10, 1.50)
        with open(isolated_costs_log, "a") as f:
            f.write("\n\n")
        _write_cost_entry(isolated_costs_log, now - 5, 2.50)

        total = costs._load_costs_since(now - 20)
        assert total == pytest.approx(4.00)


# ---------------------------------------------------------------------------
# Budget enforcement
# ---------------------------------------------------------------------------

class TestCheckBudget:
    def test_no_limits_set_passes(self):
        # No env vars set — should not raise
        costs._check_budget()

    def test_daily_budget_under_limit_passes(self, isolated_costs_log, monkeypatch):
        monkeypatch.setenv("DAILY_BUDGET", "10.00")
        now = time.time()
        _write_cost_entry(isolated_costs_log, now - 10, 5.00)
        costs._check_budget()  # should not raise

    def test_daily_budget_at_limit_raises(self, isolated_costs_log, monkeypatch):
        monkeypatch.setenv("DAILY_BUDGET", "5.00")
        now = time.time()
        _write_cost_entry(isolated_costs_log, now - 10, 5.00)

        with pytest.raises(costs.BudgetExceededError, match="Daily budget"):
            costs._check_budget()

    def test_daily_budget_over_limit_raises(self, isolated_costs_log, monkeypatch):
        monkeypatch.setenv("DAILY_BUDGET", "5.00")
        now = time.time()
        _write_cost_entry(isolated_costs_log, now - 10, 7.00)

        with pytest.raises(costs.BudgetExceededError, match="Daily budget"):
            costs._check_budget()

    def test_monthly_budget_at_limit_raises(self, isolated_costs_log, monkeypatch):
        monkeypatch.setenv("MONTHLY_BUDGET", "20.00")
        now = time.time()
        _write_cost_entry(isolated_costs_log, now - 10, 20.00)

        with pytest.raises(costs.BudgetExceededError, match="Monthly budget"):
            costs._check_budget()

    def test_daily_checked_before_monthly(self, isolated_costs_log, monkeypatch):
        """If both limits are exceeded, daily should be reported first."""
        monkeypatch.setenv("DAILY_BUDGET", "1.00")
        monkeypatch.setenv("MONTHLY_BUDGET", "1.00")
        now = time.time()
        _write_cost_entry(isolated_costs_log, now - 10, 2.00)

        with pytest.raises(costs.BudgetExceededError, match="Daily"):
            costs._check_budget()

    def test_error_message_includes_spent_amount(self, isolated_costs_log, monkeypatch):
        monkeypatch.setenv("DAILY_BUDGET", "5.00")
        now = time.time()
        _write_cost_entry(isolated_costs_log, now - 10, 6.50)

        with pytest.raises(costs.BudgetExceededError) as exc_info:
            costs._check_budget()
        assert "$6.50" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Log writing
# ---------------------------------------------------------------------------

class TestLogCall:
    def test_appends_entry_to_log(self, isolated_costs_log):
        costs._log_call("claude-sonnet-4-6", 1000, 200, 0.006)

        with open(isolated_costs_log) as f:
            lines = f.readlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["model"] == "claude-sonnet-4-6"
        assert entry["input_tokens"] == 1000
        assert entry["output_tokens"] == 200
        assert entry["cost_usd"] == 0.006
        assert "timestamp" in entry
        assert "datetime" in entry

    def test_multiple_entries_accumulate(self, isolated_costs_log):
        costs._log_call("claude-sonnet-4-6", 100, 50, 0.001)
        costs._log_call("claude-haiku-4-5-20251001", 200, 100, 0.0002)

        with open(isolated_costs_log) as f:
            lines = f.readlines()
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# TrackedMessages proxy
# ---------------------------------------------------------------------------

class TestTrackedMessages:
    def test_create_logs_and_returns_response(self, isolated_costs_log):
        """Verify create() calls through, logs cost, and returns the response."""
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 500
        mock_response.usage.output_tokens = 100

        mock_messages = MagicMock()
        mock_messages.create.return_value = mock_response

        tracked = costs._TrackedMessages(mock_messages)
        result = tracked.create(model="claude-sonnet-4-6", max_tokens=100)

        assert result is mock_response
        mock_messages.create.assert_called_once_with(
            model="claude-sonnet-4-6", max_tokens=100
        )
        # Verify a log entry was written
        with open(isolated_costs_log) as f:
            entry = json.loads(f.readline())
        assert entry["model"] == "claude-sonnet-4-6"
        assert entry["input_tokens"] == 500
        assert entry["output_tokens"] == 100

    def test_create_checks_budget_before_calling(self, isolated_costs_log, monkeypatch):
        """Verify budget is checked before the API call is made."""
        monkeypatch.setenv("DAILY_BUDGET", "0.01")
        now = time.time()
        _write_cost_entry(isolated_costs_log, now - 10, 1.00)

        mock_messages = MagicMock()
        tracked = costs._TrackedMessages(mock_messages)

        with pytest.raises(costs.BudgetExceededError):
            tracked.create(model="claude-sonnet-4-6")

        # The underlying API should NOT have been called
        mock_messages.create.assert_not_called()

    def test_getattr_passes_through_other_methods(self):
        """Verify that unwrapped methods like stream() are accessible."""
        mock_messages = MagicMock()
        mock_messages.stream.return_value = "streamed"

        tracked = costs._TrackedMessages(mock_messages)
        result = tracked.stream(model="claude-sonnet-4-6")

        assert result == "streamed"
        mock_messages.stream.assert_called_once()
