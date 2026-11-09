"""Unit & Integration Tests for AegisLake Streaming Engine and Data Contracts."""

import pytest
from pydantic import ValidationError

from aegis_streaming.contracts import (
    CardAuthorizationEvent,
    ClearinghouseSettlementEvent,
    FXSwapEvent,
)
from aegis_streaming.producer import PaymentStreamProducer
from aegis_streaming.chaos_engine import ChaosEngine


class TestDataContracts:
    """Validates contract invariants and currency decimal scaling."""

    def test_card_auth_eur_scaling(self):
        auth = CardAuthorizationEvent(
            authorization_id="auth_001",
            idempotency_key="idem_001",
            customer_id="cust_100",
            merchant_id="m_zara",
            amount_minor=1999,  # €19.99
            currency="EUR",
            card_last4="4242",
        )
        assert auth.amount_minor == 1999
        assert auth.amount_base == 19.99

    def test_card_auth_jpy_zero_decimal_scaling(self):
        auth = CardAuthorizationEvent(
            authorization_id="auth_002",
            idempotency_key="idem_002",
            customer_id="cust_101",
            merchant_id="m_uniqlo",
            amount_minor=5000,  # ¥5000 (No decimals)
            currency="JPY",
            card_last4="1111",
        )
        assert auth.amount_minor == 5000
        assert auth.amount_base == 5000.0  # Must NOT be 50.0!

    def test_negative_amount_violates_invariant(self):
        with pytest.raises(ValidationError):
            CardAuthorizationEvent(
                authorization_id="auth_003",
                idempotency_key="idem_003",
                customer_id="cust_102",
                merchant_id="m_test",
                amount_minor=-100,  # Invalid!
                currency="EUR",
                card_last4="0000",
            )

    def test_invalid_currency_rejected(self):
        with pytest.raises(ValidationError):
            CardAuthorizationEvent(
                authorization_id="auth_004",
                idempotency_key="idem_004",
                customer_id="cust_103",
                merchant_id="m_test",
                amount_minor=500,
                currency="ZZZ",  # Not an ISO currency in our contract
                card_last4="9999",
            )

    def test_fx_swap_same_currency_rejected(self):
        with pytest.raises(ValidationError):
            FXSwapEvent(
                swap_id="fx_001",
                base_currency="EUR",
                quote_currency="EUR",  # Must be different!
                base_amount_minor=100000,
                quote_amount_minor=100000,
                effective_rate=1.0,
                counterparty="BARCLAYS",
            )


class TestPaymentProducer:
    """Validates the synthetic payment stream generation."""

    def test_producer_generates_valid_events(self):
        producer = PaymentStreamProducer(customer_pool_size=10, seed=42)
        auth = producer.generate_authorization()

        assert auth.authorization_id.startswith("auth_")
        assert auth.idempotency_key.startswith("idem_")
        assert auth.amount_minor > 0
        assert auth.currency in ["EUR", "USD", "GBP", "JPY"]

    def test_producer_generates_synchronized_pair(self):
        producer = PaymentStreamProducer(customer_pool_size=10, seed=42)
        auth, settlement = producer.generate_pair(settlement_delay_sec=3)

        assert settlement.authorization_id == auth.authorization_id
        assert settlement.settled_amount_minor == auth.amount_minor
        assert settlement.currency == auth.currency
        assert settlement.fee_minor > 0

    def test_producer_batch_generation(self):
        producer = PaymentStreamProducer(customer_pool_size=20, seed=42)
        auths, settlements = producer.generate_batch(batch_size=50, settlement_ratio=0.9)

        assert len(auths) == 50
        assert len(settlements) <= 50
        assert len(settlements) >= 40  # Statistical range for 90%


class TestChaosEngine:
    """Validates anomaly injection and error tagging."""

    def test_jpy_decimal_anomaly_injection(self):
        producer = PaymentStreamProducer(seed=42)
        auth = producer.generate_authorization(currency="JPY", amount_minor=10000)
        corrupted = ChaosEngine.inject_jpy_decimal_anomaly(auth)

        assert corrupted["currency"] == "JPY"
        assert corrupted["amount_minor"] == 100  # Corrupted by division by 100!
        assert corrupted["_chaos_tag"] == "ERR_JPY_DECIMAL_SCALING"

    def test_schema_drift_fails_contract_validation(self):
        producer = PaymentStreamProducer(seed=42)
        auth = producer.generate_authorization()
        corrupted = ChaosEngine.inject_schema_drift(auth)

        assert corrupted["_chaos_tag"] == "ERR_SCHEMA_DRIFT"
        assert "idempotency_key" not in corrupted

        # Contract validator MUST reject this corrupted payload
        with pytest.raises(ValidationError):
            CardAuthorizationEvent(**corrupted)

    def test_duplicate_storm_replays_identical_keys(self):
        producer = PaymentStreamProducer(seed=42)
        auth = producer.generate_authorization()
        duplicates = ChaosEngine.inject_duplicate_storm(auth, duplicate_count=4)

        assert len(duplicates) == 4
        # All duplicates must share the exact same authorization_id and idempotency_key
        assert all(d["authorization_id"] == auth.authorization_id for d in duplicates)
        assert all(d["idempotency_key"] == auth.idempotency_key for d in duplicates)
