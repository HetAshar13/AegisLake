"""High-Throughput Multi-Rail Payment Generator for AegisLake.

Generates realistic Card, SEPA, and FX streams with configurable TPS,
ISO-4217 minor unit amounts, and temporal settlement offsets.
"""

import json
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generator, List, Optional, Tuple
from uuid import uuid4

from aegis_streaming.contracts import (
    CURRENCY_EXPONENTS,
    AuthorizationStatus,
    CardAuthorizationEvent,
    ClearinghouseSettlementEvent,
    PaymentRail,
    SettlementStatus,
)


MERCHANTS = [
    {"merchant_id": "m_amazon_eu", "mcc": "5311", "name": "Amazon EU SARL"},
    {"merchant_id": "m_zara_milan", "mcc": "5651", "name": "Zara Corso Vittorio Emanuele"},
    {"merchant_id": "m_esselunga_mi", "mcc": "5411", "name": "Esselunga Supermercati"},
    {"merchant_id": "m_booking_ams", "mcc": "7011", "name": "Booking.com B.V."},
    {"merchant_id": "m_uber_bv", "mcc": "4121", "name": "Uber Payments B.V."},
    {"merchant_id": "m_apple_irl", "mcc": "5732", "name": "Apple Distribution International"},
]

CLEARINGHOUSES = [
    "VISA_INTERCHANGE",
    "MASTERCARD_CLEARING",
    "TARGET2",
    "STEP2",
]


class PaymentStreamProducer:
    """Generates synthetic high-velocity multi-rail payment transactions."""

    def __init__(
        self,
        customer_pool_size: int = 5000,
        currencies: Optional[List[str]] = None,
        seed: Optional[int] = 42,
    ):
        if seed is not None:
            random.seed(seed)
        self.customers = [f"cust_{uuid4().hex[:10]}" for _ in range(customer_pool_size)]
        self.currencies = currencies or ["EUR", "EUR", "EUR", "USD", "GBP", "JPY"]

    def generate_authorization(
        self,
        customer_id: Optional[str] = None,
        currency: Optional[str] = None,
        amount_minor: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ) -> CardAuthorizationEvent:
        """Generates a single valid CardAuthorizationEvent."""
        cid = customer_id or random.choice(self.customers)
        curr = currency or random.choice(self.currencies)
        merchant = random.choice(MERCHANTS)
        
        if amount_minor is None:
            if curr == "JPY":
                # Typical JPY transactions: ¥800 to ¥65,000
                amount_minor = random.randint(800, 65000)
            else:
                # EUR / USD / GBP: €5.00 to €850.00 (in minor cents)
                amount_minor = random.randint(500, 85000)

        auth_id = f"auth_{uuid4().hex[:16]}"
        idem_key = f"idem_{uuid4().hex[:20]}"
        card_last4 = f"{random.randint(1000, 9999)}"

        return CardAuthorizationEvent(
            authorization_id=auth_id,
            idempotency_key=idem_key,
            customer_id=cid,
            merchant_id=merchant["merchant_id"],
            merchant_mcc=merchant["mcc"],
            amount_minor=amount_minor,
            currency=curr,
            card_last4=card_last4,
            status=AuthorizationStatus.AUTHORIZED,
            authorized_at=timestamp or datetime.now(timezone.utc),
        )

    def generate_settlement_for_auth(
        self,
        auth: CardAuthorizationEvent,
        delay_seconds: int = 0,
        fee_basis_points: int = 25,  # 0.25% interchange fee
    ) -> ClearinghouseSettlementEvent:
        """Generates a matching ClearinghouseSettlementEvent for a given authorization."""
        settlement_id = f"stl_{uuid4().hex[:16]}"
        clearinghouse = random.choice(CLEARINGHOUSES)
        batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
        
        # Calculate fee in minor units: fee = amount * (bps / 10000)
        fee_minor = max(1, int(auth.amount_minor * (fee_basis_points / 10000.0)))
        settled_at = auth.authorized_at + timedelta(seconds=delay_seconds)

        return ClearinghouseSettlementEvent(
            settlement_id=settlement_id,
            authorization_id=auth.authorization_id,
            clearinghouse=clearinghouse,
            settled_amount_minor=auth.amount_minor,
            fee_minor=fee_minor,
            currency=auth.currency,
            settlement_status=SettlementStatus.SETTLED,
            batch_id=batch_id,
            settled_at=settled_at,
        )

    def generate_pair(
        self,
        settlement_delay_sec: int = 2,
    ) -> Tuple[CardAuthorizationEvent, ClearinghouseSettlementEvent]:
        """Generates a synchronized (Authorization, Settlement) pair."""
        auth = self.generate_authorization()
        settlement = self.generate_settlement_for_auth(auth, delay_seconds=settlement_delay_sec)
        return auth, settlement

    def generate_batch(
        self,
        batch_size: int = 1000,
        settlement_ratio: float = 0.95,
    ) -> Tuple[List[CardAuthorizationEvent], List[ClearinghouseSettlementEvent]]:
        """Generates a batch of authorizations and their corresponding settlements.
        
        settlement_ratio simulates realistic real-world settlement timing:
        e.g., 95% settle immediately, while 5% are in-flight / pending settlement.
        """
        auths: List[CardAuthorizationEvent] = []
        settlements: List[ClearinghouseSettlementEvent] = []

        for _ in range(batch_size):
            auth = self.generate_authorization()
            auths.append(auth)
            if random.random() < settlement_ratio:
                settlement = self.generate_settlement_for_auth(auth, delay_seconds=random.randint(1, 10))
                settlements.append(settlement)

        return auths, settlements
