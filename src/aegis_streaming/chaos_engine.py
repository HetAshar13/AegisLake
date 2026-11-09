"""Chaos Engine & Anomaly Injector for AegisLake.

Injects controlled synthetic pipeline corruptions to validate lakehouse
contract enforcement, quarantine routing, and AI Copilot diagnosis.
"""

import copy
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import uuid4

from aegis_streaming.contracts import CardAuthorizationEvent, ClearinghouseSettlementEvent


class ChaosEngine:
    """Simulates production pipeline failures, schema drifts, and accounting anomalies."""

    @staticmethod
    def inject_jpy_decimal_anomaly(auth: CardAuthorizationEvent) -> Dict[str, Any]:
        """Corrupts JPY amounts by erroneously dividing by 100 or scaling as EUR cents.

        This mimics a junior engineer treating all currencies as having 2 decimal places.
        """
        payload = auth.model_dump()
        payload["currency"] = "JPY"
        # Erroneous scaling: original ¥5000 becomes 50 minor units
        payload["amount_minor"] = max(1, auth.amount_minor // 100)
        payload["_chaos_tag"] = "ERR_JPY_DECIMAL_SCALING"
        return payload

    @staticmethod
    def inject_negative_amount(auth: CardAuthorizationEvent) -> Dict[str, Any]:
        """Injects a negative transaction amount (violates positive balance invariant)."""
        payload = auth.model_dump()
        payload["amount_minor"] = -abs(auth.amount_minor)
        payload["_chaos_tag"] = "ERR_NEGATIVE_AMOUNT"
        return payload

    @staticmethod
    def inject_schema_drift(auth: CardAuthorizationEvent) -> Dict[str, Any]:
        """Injects un-announced upstream schema changes (string amount, missing idempotency)."""
        payload = auth.model_dump()
        # Corrupt type: string instead of integer
        payload["amount_minor"] = f"{auth.amount_minor}.00"
        # Delete required field
        del payload["idempotency_key"]
        # Add rogue un-contracted field
        payload["experimental_v3_feature"] = "unauthorized_payload_expansion"
        payload["_chaos_tag"] = "ERR_SCHEMA_DRIFT"
        return payload

    @staticmethod
    def inject_settlement_break(
        auth: CardAuthorizationEvent,
        mismatch_delta_minor: int = 500,  # e.g., €5.00 discrepancy
    ) -> Dict[str, Any]:
        """Injects an amount discrepancy between internal authorization and clearinghouse settlement."""
        settlement_payload = {
            "event_id": str(uuid4()),
            "settlement_id": f"stl_{uuid4().hex[:16]}",
            "authorization_id": auth.authorization_id,
            "clearinghouse": "VISA_INTERCHANGE",
            # Amount does NOT match auth:
            "settled_amount_minor": auth.amount_minor + mismatch_delta_minor,
            "fee_minor": 25,
            "currency": auth.currency,
            "settlement_status": "SETTLED",
            "batch_id": f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d%H')}",
            "settled_at": (auth.authorized_at + timedelta(seconds=5)).isoformat(),
            "_chaos_tag": "ERR_RECONCILIATION_AMOUNT_MISMATCH",
        }
        return settlement_payload

    @staticmethod
    def inject_duplicate_storm(
        auth: CardAuthorizationEvent,
        duplicate_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """Replays identical authorization payloads to test streaming deduplication."""
        duplicates: List[Dict[str, Any]] = []
        base_payload = auth.model_dump()
        for i in range(duplicate_count):
            dup = copy.deepcopy(base_payload)
            dup["_chaos_tag"] = f"ERR_DUPLICATE_STORM_REPLAY_{i + 1}"
            duplicates.append(dup)
        return duplicates

    @staticmethod
    def inject_late_arriving_event(
        auth: CardAuthorizationEvent,
        delay_minutes: int = 35,  # Exceeds standard 10-minute watermark
    ) -> Dict[str, Any]:
        """Generates an event with an event-time far older than the stream watermark."""
        payload = auth.model_dump()
        old_timestamp = datetime.now(timezone.utc) - timedelta(minutes=delay_minutes)
        payload["authorized_at"] = old_timestamp.isoformat()
        payload["_chaos_tag"] = "ERR_LATE_ARRIVING_WATERMARK_BREACH"
        return payload
