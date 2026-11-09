"""AegisLake Pipeline Runner: Generates Live Events & Builds Delta Lake Tables.

Connects Module 1 (Streaming Producer + Chaos Engine) to Module 2 (PySpark Medallion Lakehouse)
and persists real Delta Lake tables to disk for downstream dbt consumption (Module 3).
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from aegis_streaming.producer import PaymentStreamProducer
from aegis_streaming.chaos_engine import ChaosEngine
from aegis_lakehouse.spark_session import create_aegis_spark_session
from aegis_lakehouse.reconciliation import run_three_way_reconciliation


def main():
    print("[1/4] Generating 100 Multi-Rail Payment Events with Chaos Simulation...")
    producer = PaymentStreamProducer(customer_pool_size=50, seed=42)

    auth_rows = []
    settle_rows = []
    ledger_rows = []

    for i in range(100):
        auth, settle = producer.generate_pair(settlement_delay_sec=30)

        auth_rows.append(
            {
                "authorization_id": auth.authorization_id,
                "idempotency_key": auth.idempotency_key,
                "customer_id": auth.customer_id,
                "merchant_id": auth.merchant_id,
                "merchant_mcc": auth.merchant_mcc,
                "amount_minor": int(auth.amount_minor),
                "currency": auth.currency,
                "card_last4": auth.card_last4,
                "status": auth.status.value,
                "authorized_at": auth.authorized_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        if i % 12 == 0:
            # Amount Mismatch Break (e.g. restaurant tip or FX variance)
            settle_dict = ChaosEngine.inject_settlement_break(auth, mismatch_delta_minor=750)
            settle_rows.append(
                {
                    "settlement_id": settle_dict["settlement_id"],
                    "authorization_id": settle_dict["authorization_id"],
                    "clearinghouse": settle_dict["clearinghouse"],
                    "settled_amount_minor": int(settle_dict["settled_amount_minor"]),
                    "fee_minor": int(settle_dict["fee_minor"]),
                    "settled_currency": settle_dict["currency"],
                    "settlement_status": settle_dict["settlement_status"],
                    "batch_id": settle_dict["batch_id"],
                    "settled_at": str(settle_dict["settled_at"])[:19],
                }
            )
            ledger_rows.append(
                {
                    "ledger_entry_id": f"led_{i:04d}",
                    "authorization_id": settle_dict["authorization_id"],
                    "account_id": "ACC_GL_1001",
                    "ledger_amount_minor": int(settle_dict["settled_amount_minor"]),
                    "currency": settle_dict["currency"],
                    "entry_type": "DEBIT",
                    "posted_at": str(settle_dict["settled_at"])[:19],
                }
            )
        elif i % 15 == 0:
            # Unmatched Authorization (settlement never arrives)
            pass
        elif i % 20 == 0:
            # Currency Mismatch Break
            settle_rows.append(
                {
                    "settlement_id": settle.settlement_id,
                    "authorization_id": auth.authorization_id,
                    "clearinghouse": settle.clearinghouse,
                    "settled_amount_minor": int(settle.settled_amount_minor),
                    "fee_minor": int(settle.fee_minor),
                    "settled_currency": "USD" if auth.currency == "EUR" else "EUR",
                    "settlement_status": settle.settlement_status.value,
                    "batch_id": settle.batch_id,
                    "settled_at": settle.settled_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            ledger_rows.append(
                {
                    "ledger_entry_id": f"led_{i:04d}",
                    "authorization_id": auth.authorization_id,
                    "account_id": "ACC_GL_1001",
                    "ledger_amount_minor": int(settle.settled_amount_minor),
                    "currency": settle.currency,
                    "entry_type": "DEBIT",
                    "posted_at": settle.settled_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        else:
            # Clean Matched Transaction
            settle_rows.append(
                {
                    "settlement_id": settle.settlement_id,
                    "authorization_id": settle.authorization_id,
                    "clearinghouse": settle.clearinghouse,
                    "settled_amount_minor": int(settle.settled_amount_minor),
                    "fee_minor": int(settle.fee_minor),
                    "settled_currency": settle.currency,
                    "settlement_status": settle.settlement_status.value,
                    "batch_id": settle.batch_id,
                    "settled_at": settle.settled_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            ledger_rows.append(
                {
                    "ledger_entry_id": f"led_{i:04d}",
                    "authorization_id": settle.authorization_id,
                    "account_id": "ACC_GL_1001",
                    "ledger_amount_minor": int(settle.settled_amount_minor),
                    "currency": settle.currency,
                    "entry_type": "DEBIT",
                    "posted_at": settle.settled_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    # Add 5 phantom settlements
    for j in range(5):
        phantom_auth = producer.generate_authorization()
        phantom_settle = producer.generate_settlement_for_auth(phantom_auth)
        settle_rows.append(
            {
                "settlement_id": phantom_settle.settlement_id,
                "authorization_id": f"phantom_auth_{j:03d}",
                "clearinghouse": phantom_settle.clearinghouse,
                "settled_amount_minor": int(phantom_settle.settled_amount_minor),
                "fee_minor": int(phantom_settle.fee_minor),
                "settled_currency": phantom_settle.currency,
                "settlement_status": phantom_settle.settlement_status.value,
                "batch_id": phantom_settle.batch_id,
                "settled_at": phantom_settle.settled_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    staging_dir = Path("data/staging_raw")
    staging_dir.mkdir(parents=True, exist_ok=True)

    auth_json = staging_dir / "raw_auth.json"
    settle_json = staging_dir / "raw_settle.json"
    ledger_json = staging_dir / "raw_ledger.json"

    with open(auth_json, "w", encoding="utf-8") as f:
        for r in auth_rows:
            f.write(json.dumps(r) + "\n")

    with open(settle_json, "w", encoding="utf-8") as f:
        for r in settle_rows:
            f.write(json.dumps(r) + "\n")

    with open(ledger_json, "w", encoding="utf-8") as f:
        for r in ledger_rows:
            f.write(json.dumps(r) + "\n")

    print("[2/4] Booting AegisLake PySpark Engine with Delta Lake 3.2...")
    spark = create_aegis_spark_session("aegislake_live_pipeline")
    spark.sparkContext.setLogLevel("ERROR")

    auth_df = spark.read.json(str(auth_json))
    settle_df = spark.read.json(str(settle_json))
    ledger_df = spark.read.json(str(ledger_json))

    base_path = Path("data/lakehouse")
    base_path.mkdir(parents=True, exist_ok=True)

    silver_auth_path = (base_path / "silver_authorizations").as_posix()
    silver_breaks_path = (base_path / "silver_reconciliation_breaks").as_posix()

    print("[3/4] Persisting Clean Silver Authorizations Delta Table...")
    auth_df.write.format("delta").mode("overwrite").save(silver_auth_path)
    print(f"      -> Successfully saved {auth_df.count()} authorizations to {silver_auth_path}")

    print("[4/4] Executing Three-Way Reconciliation and Persisting Breaks Delta Table...")
    recon_df = run_three_way_reconciliation(auth_df, settle_df, ledger_df)
    recon_df.write.format("delta").mode("overwrite").save(silver_breaks_path)
    print(f"      -> Successfully saved {recon_df.count()} reconciliation records to {silver_breaks_path}")

    print("\nSUCCESS: All Delta Lake tables written successfully!")
    spark.stop()


if __name__ == "__main__":
    main()
