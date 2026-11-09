"""
AegisLake Module 5: Real-World Payment Stream Replay Engine
Simulates Poisson arrival processes and ISO-18245 merchant category distributions.
"""

from typing import Dict, Any, Generator, Optional, List
import random
import math
import time
from datetime import datetime


# Standard ISO-18245 Merchant Distribution in Retail Banking
MERCHANT_DISTRIBUTION = [
    {"mcc": "5411", "category": "Grocery", "weight": 40, "amount_range": (5.0, 150.0)},
    {"mcc": "5812", "category": "Restaurants", "weight": 25, "amount_range": (10.0, 95.0)},
    {"mcc": "4111", "category": "Transport", "weight": 15, "amount_range": (1.50, 25.0)},
    {"mcc": "5311", "category": "Department Stores", "weight": 12, "amount_range": (25.0, 300.0)},
    {"mcc": "5541", "category": "Fuel / Service Stations", "weight": 8, "amount_range": (30.0, 120.0)},
]

# Standard ISO-4217 Currency Distribution
CURRENCY_WEIGHTS = [
    ("EUR", 2, 70),  # 70% EUR (2 decimals)
    ("USD", 2, 20),  # 20% USD (2 decimals)
    ("GBP", 2, 8),   # 8% GBP (2 decimals)
    ("JPY", 0, 2),   # 2% JPY (0 decimals)
]


def calculate_poisson_inter_arrival(lambda_rate: float) -> float:
    """
    Calculates the inter-arrival time (in seconds) between consecutive transactions
    following an Exponential distribution: delta_t = -ln(U) / lambda.

    Args:
        lambda_rate (float): Target arrival rate (transactions per second, lambda > 0).

    Returns:
        float: Inter-arrival wait time in seconds (minimum 0.0001s).
    """
    if lambda_rate <= 0:
        lambda_rate = 1.0

    # Sample U in (0, 1] avoiding exact zero
    u = max(random.random(), 1e-9)
    # Compute exponential wait time: delta_t = -ln(U) / lambda
    return max(-math.log(u) / lambda_rate, 0.0001)


def sample_realistic_transaction(transaction_seq: int = 1) -> Dict[str, Any]:
    """
    Generates a single high-fidelity transaction dictionary modeled on real-world retail banking distributions.
    """
    # 1. Weighted random selection of merchant category
    merchant = random.choices(
        MERCHANT_DISTRIBUTION,
        weights=[m["weight"] for m in MERCHANT_DISTRIBUTION]
    )[0]

    # 2. Weighted random selection of currency
    curr_tuple = random.choices(
        CURRENCY_WEIGHTS,
        weights=[c[2] for c in CURRENCY_WEIGHTS]
    )[0]
    currency_code, exponent, _ = curr_tuple

    # 3. Sample amount from merchant's typical range
    amount = random.uniform(*merchant["amount_range"])
    amount_minor = int(round(amount * (10 ** exponent)))
    amount_scaled = round(amount, 2 if exponent > 0 else 0)

    # 4. Construct realistic transaction payload
    return {
        "authorization_id": f"AUTH_{transaction_seq:06d}",
        "timestamp": datetime.now().isoformat(),
        "customer_id": f"cust_{random.randint(1000, 9999)}",
        "merchant_mcc": merchant["mcc"],
        "merchant_category": merchant["category"],
        "currency": currency_code,
        "exponent": exponent,
        "amount_scaled": amount_scaled,
        "amount_minor": amount_minor,
        "card_bin": random.choice(["424242", "555555", "400000", "510510"]),
        "rail": random.choice(["Revolut Pay", "Visa Direct", "Mastercard Cleared", "SEPA Instant"]),
    }


def stream_realistic_transactions(
    total_events: int = 10,
    lambda_rate: float = 15.0,
    simulate_sleep: bool = False
) -> Generator[Dict[str, Any], None, None]:
    """
    Yields realistic transactions with Poisson inter-arrival delays.
    """
    for i in range(1, total_events + 1):
        if simulate_sleep:
            delay = calculate_poisson_inter_arrival(lambda_rate)
            time.sleep(delay)
        yield sample_realistic_transaction(transaction_seq=i)
