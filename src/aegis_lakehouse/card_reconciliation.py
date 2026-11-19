"""Three-way assessment at the grain of one synthetic card authorization."""

from pyspark.sql import functions as F


def assess_card_payments(auth, settlement, ledger, as_of, grace_minutes):
    a = auth.selectExpr(
        "authorization_id", "event_id AS auth_event_id", "amount_minor AS auth_amount_minor",
        "currency AS auth_currency", "authorized_at", "merchant_id", "customer_id"
    )
    s = settlement.selectExpr(
        "authorization_id", "event_id AS settlement_event_id", "settled_amount_minor",
        "settled_currency", "settled_at", "fee_minor"
    )
    l = ledger.selectExpr(
        "authorization_id", "event_id AS ledger_event_id", "ledger_amount_minor",
        "currency AS ledger_currency", "posted_at", "entry_type"
    )
    cases = a.join(s, "authorization_id", "full").join(l, "authorization_id", "full")
    has_auth = F.col("auth_event_id").isNotNull()
    has_settlement = F.col("settlement_event_id").isNotNull()
    has_ledger = F.col("ledger_event_id").isNotNull()
    cutoff = F.lit(as_of.isoformat()).cast("timestamp")
    deadline = F.col("authorized_at").cast("timestamp") + F.expr(f"INTERVAL {grace_minutes} MINUTES")
    eligible_settlement = has_auth & has_settlement & (F.col("auth_currency") == F.col("settled_currency"))
    eligible_ledger = has_settlement & has_ledger & (F.col("ledger_currency") == F.col("settled_currency"))
    settlement_delta = F.when(eligible_settlement, F.col("settled_amount_minor") - F.col("auth_amount_minor"))
    ledger_delta = F.when(eligible_ledger, F.col("ledger_amount_minor") - F.col("settled_amount_minor"))
    reasons = [
        (has_ledger & ~has_auth & ~has_settlement, "BREAK_ORPHAN_LEDGER"),
        (~has_auth & has_settlement, "BREAK_UNMATCHED_SETTLEMENT"),
        (has_auth & ~has_settlement & (cutoff >= deadline), "BREAK_UNMATCHED_AUTHORIZATION"),
        (has_auth & has_settlement & ~eligible_settlement, "BREAK_CURRENCY_MISMATCH"),
        (settlement_delta != 0, "BREAK_AMOUNT_MISMATCH"),
        (has_settlement & ~has_ledger, "BREAK_MISSING_LEDGER"),
        (has_settlement & has_ledger & ~eligible_ledger, "BREAK_LEDGER_CURRENCY_MISMATCH"),
        (has_ledger & (F.col("entry_type") != "DEBIT"), "BREAK_LEDGER_DIRECTION"),
        (ledger_delta != 0, "BREAK_LEDGER_AMOUNT_MISMATCH"),
    ]
    return (
        cases.withColumn("break_reasons", F.array_compact(F.array(*[F.when(c, F.lit(s)) for c, s in reasons])))
        .withColumn("reconciliation_status",
            F.when(F.size("break_reasons") > 0, F.element_at("break_reasons", 1))
            .when(~has_settlement, F.lit("PENDING"))
            .otherwise(F.lit("MATCHED")))
        .withColumn("is_actionable_break", F.size("break_reasons") > 0)
        .withColumn("discrepancy_amount", settlement_delta)
        .withColumn("ledger_discrepancy_minor", ledger_delta)
        .withColumn("currency", F.coalesce("auth_currency", "settled_currency", "ledger_currency"))
        .withColumn("reconciled_at", cutoff)
    )
