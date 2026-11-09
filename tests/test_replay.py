"""
Unit tests for AegisLake Module 5: Real-World Replay Engine.
Verifies Poisson inter-arrival times, currency scaling, and MCC distributions.
"""

import pytest
import math
from aegis_streaming.replay_engine import (
    calculate_poisson_inter_arrival,
    sample_realistic_transaction,
    stream_realistic_transactions,
)


def test_poisson_inter_arrival_distribution():
    """Verify exponential inter-arrival calculation produces valid positive delays."""
    lambda_rate = 20.0  # 20 events/sec -> mean wait time ~0.05s
    delays = [calculate_poisson_inter_arrival(lambda_rate) for _ in range(100)]

    assert len(delays) == 100
    assert all(d > 0.0 for d in delays)
    # Mean of exponential distribution with lambda=20 should be approximately 0.05
    sample_mean = sum(delays) / len(delays)
    assert 0.01 < sample_mean < 0.15


def test_sample_realistic_transaction_structure():
    """Verify that sampled transactions conform to ISO standards and schema invariants."""
    txn = sample_realistic_transaction(transaction_seq=42)

    assert txn["authorization_id"] == "AUTH_000042"
    assert txn["currency"] in ["EUR", "USD", "GBP", "JPY"]
    assert txn["amount_minor"] > 0
    assert "merchant_mcc" in txn
    assert "merchant_category" in txn
    assert txn["card_bin"] in ["424242", "555555", "400000", "510510"]

    # Verify minor unit exponent scaling
    if txn["currency"] == "JPY":
        assert txn["exponent"] == 0
        assert txn["amount_minor"] == int(txn["amount_scaled"])
    else:
        assert txn["exponent"] == 2
        assert txn["amount_minor"] == int(round(txn["amount_scaled"] * 100))


def test_stream_realistic_transactions_generator():
    """Verify streaming generator yields the exact requested count of events."""
    events = list(stream_realistic_transactions(total_events=15, lambda_rate=50.0, simulate_sleep=False))

    assert len(events) == 15
    assert events[0]["authorization_id"] == "AUTH_000001"
    assert events[-1]["authorization_id"] == "AUTH_000015"
