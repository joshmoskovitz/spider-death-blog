#!/usr/bin/env python3
"""
Spider Death Blog — Cost Tracking & Budget Enforcement

Wraps the Anthropic client to log every API call and enforce spending caps.
Costs are logged to costs.jsonl (one JSON object per line).

Budget limits are configured via environment variables:
    DAILY_BUDGET=5.00    (dollars per day, default: no limit)
    MONTHLY_BUDGET=50.00 (dollars per month, default: no limit)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

PROJECT_DIR = Path(__file__).parent
COSTS_LOG = PROJECT_DIR / "costs.jsonl"

# Pricing per million tokens (input, output) as of 2025
PRICE_TABLE = {
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (0.80, 4.00),
}

# Fallback for unknown models — use the most expensive rate to be safe
_DEFAULT_PRICE = (3.00, 15.00)


class BudgetExceededError(Exception):
    """Raised when a spending cap has been reached."""
    pass


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost in dollars for a single API call."""
    if model not in PRICE_TABLE:
        print(
            f"[costs] WARNING: unknown model '{model}', using fallback pricing. "
            f"Update PRICE_TABLE in costs.py.",
            file=sys.stderr,
        )
    input_rate, output_rate = PRICE_TABLE.get(model, _DEFAULT_PRICE)
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000


def _load_costs_since(since_timestamp: float) -> float:
    """Sum all costs from the log file since a given Unix timestamp.

    Reads the file in reverse so we can stop as soon as we hit entries
    older than our cutoff, avoiding a full scan of the entire history.
    """
    total = 0.0
    if not COSTS_LOG.exists():
        return total

    # Read all lines, then iterate in reverse (entries are chronological)
    with open(COSTS_LOG) as f:
        lines = f.readlines()

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            ts = entry.get("timestamp", 0)
            if ts >= since_timestamp:
                total += entry.get("cost_usd", 0)
            else:
                # Entries are chronological — no older entries will match
                break
        except json.JSONDecodeError:
            continue
    return total


def daily_total() -> float:
    """Total spend today (UTC)."""
    now = datetime.now(timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return _load_costs_since(midnight.timestamp())


def monthly_total() -> float:
    """Total spend this calendar month (UTC)."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return _load_costs_since(month_start.timestamp())


def _check_budget():
    """Raise BudgetExceededError if a spending cap has been reached.

    NOTE: There is an inherent TOCTOU race here — two concurrent requests
    could both pass the check, both make API calls, and both log costs,
    overshooting the budget. For a single-server side project this is an
    acceptable tradeoff; the budget is a guardrail, not a hard guarantee.
    """
    daily_limit = os.environ.get("DAILY_BUDGET")
    if daily_limit:
        spent = daily_total()
        if spent >= float(daily_limit):
            raise BudgetExceededError(
                f"Daily budget of ${daily_limit} reached. "
                f"Spent ${spent:.2f} today."
            )

    monthly_limit = os.environ.get("MONTHLY_BUDGET")
    if monthly_limit:
        spent = monthly_total()
        if spent >= float(monthly_limit):
            raise BudgetExceededError(
                f"Monthly budget of ${monthly_limit} reached. "
                f"Spent ${spent:.2f} this month."
            )


def _log_call(model: str, input_tokens: int, output_tokens: int, cost: float):
    """Append a cost entry to the log file."""
    entry = {
        "timestamp": time.time(),
        "datetime": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    }
    with open(COSTS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


class _TrackedMessages:
    """Wraps client.messages to intercept create() calls.

    Only create() is explicitly wrapped for cost tracking. All other
    methods (stream, count_tokens, etc.) are passed through to the
    underlying messages resource unchanged.
    """

    def __init__(self, messages):
        self._messages = messages

    def create(self, **kwargs):
        _check_budget()
        response = self._messages.create(**kwargs)

        model = kwargs.get("model", "unknown")
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = _estimate_cost(model, input_tokens, output_tokens)
        _log_call(model, input_tokens, output_tokens, cost)

        return response

    def __getattr__(self, name):
        return getattr(self._messages, name)


class TrackedClient:
    """
    Drop-in replacement for anthropic.Anthropic() that tracks costs
    and enforces budget limits.

    Usage:
        client = TrackedClient()
        # Use exactly like anthropic.Anthropic():
        client.messages.create(model="claude-sonnet-4-6", ...)
    """

    def __init__(self, **kwargs):
        self._client = anthropic.Anthropic(**kwargs)
        self.messages = _TrackedMessages(self._client.messages)

    def __getattr__(self, name):
        # Pass through any other attributes to the underlying client
        return getattr(self._client, name)
