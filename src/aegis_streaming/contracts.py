"""Financial Event Data Contracts for AegisLake.

Enforces strict ISO-4217 minor unit representations, multi-rail specifications,
and idempotency keys across all payment streams.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Literal, Optional
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator, model_validator


# ISO-4217 Currency Exponents (Number of decimal places in subunit)
CURRENCY_EXPONENTS: Dict[str, int] = {
    "EUR": 2,  # Euro Cent (1 EUR = 100 cents)
    "USD": 2,  # US Cent (1 USD = 100 cents)
    "GBP": 2,  # British Penny (1 GBP = 100 pence)
    "JPY": 0,  # Japanese Yen (Indivisible subunit: 1 Yen = 1 Yen)
    "BHD": 3,  # Bahraini Dinar (1 BHD = 1000 fils)
}


class PaymentRail(str, Enum):
    CARD = "CARD"
    SEPA_INSTANT = "SEPA_INSTANT"
    FX_SWAP = "FX_SWAP"


class AuthorizationStatus(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    DECLINED = "DECLINED"
    PENDING = "PENDING"


class SettlementStatus(str, Enum):
    SETTLED = "SETTLED"
    REJECTED = "REJECTED"
    DISPUTED = "DISPUTED"


class CardAuthorizationEvent(BaseModel):
    """Internal Card Authorization Event emitted by the core banking engine."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    authorization_id: str = Field(..., description="Server-side permanent ledger reference")
    idempotency_key: str = Field(..., description="Client-side UUID preventing double charges")
    customer_id: str = Field(..., description="Unique customer identifier for partition routing")
    merchant_id: str = Field(..., description="Merchant store account identifier")
    payment_rail: Literal[PaymentRail.CARD] = PaymentRail.CARD

    amount_minor: int = Field(..., gt=0, description="Amount in integer minor units (cents/subunits)")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO-4217 3-letter currency code")
    card_last4: str = Field(..., min_length=4, max_length=4, description="Last 4 digits of PAN")
    status: AuthorizationStatus = AuthorizationStatus.AUTHORIZED

    authorized_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    merchant_mcc: str = Field(default="5411", description="Merchant Category Code (e.g. 5411 Grocery)")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        upper = v.upper()
        if upper not in CURRENCY_EXPONENTS:
            raise ValueError(f"Unsupported currency: {v}. Must be one of {list(CURRENCY_EXPONENTS.keys())}")
        return upper

    @property
    def amount_base(self) -> float:
        """Computes true standard base currency units using the ISO-4217 exponent."""
        exponent = CURRENCY_EXPONENTS[self.currency]
        return self.amount_minor / (10**exponent)


class ClearinghouseSettlementEvent(BaseModel):
    """External Settlement Event emitted by clearinghouse network (Visa, Mastercard, TARGET2)."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    settlement_id: str = Field(..., description="Clearinghouse external transaction reference")
    authorization_id: str = Field(..., description="Matching internal authorization identifier")
    clearinghouse: str = Field(..., description="Clearinghouse network (VISA_INTERCHANGE, TARGET2, etc.)")

    settled_amount_minor: int = Field(..., gt=0, description="Settled amount in integer minor units")
    fee_minor: int = Field(default=0, ge=0, description="Interchange / network fee in minor units")
    currency: str = Field(..., min_length=3, max_length=3)
    settlement_status: SettlementStatus = SettlementStatus.SETTLED

    batch_id: str = Field(..., description="Clearinghouse settlement batch ID")
    settled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        upper = v.upper()
        if upper not in CURRENCY_EXPONENTS:
            raise ValueError(f"Unsupported currency: {v}. Must be one of {list(CURRENCY_EXPONENTS.keys())}")
        return upper

    @property
    def settled_amount_base(self) -> float:
        exponent = CURRENCY_EXPONENTS[self.currency]
        return self.settled_amount_minor / (10**exponent)


class FXSwapEvent(BaseModel):
    """Treasury FX Swap / Currency Exchange Event."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    swap_id: str = Field(..., description="Unique FX swap reference")
    base_currency: str = Field(..., min_length=3, max_length=3)
    quote_currency: str = Field(..., min_length=3, max_length=3)

    base_amount_minor: int = Field(..., gt=0)
    quote_amount_minor: int = Field(..., gt=0)
    effective_rate: float = Field(..., gt=0.0)

    counterparty: str = Field(..., description="Treasury liquidity provider (e.g. BARCLAYS_FX, CITIBANK)")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_currencies(self) -> "FXSwapEvent":
        if self.base_currency == self.quote_currency:
            raise ValueError("Base currency and quote currency cannot be identical in an FX swap")
        return self
