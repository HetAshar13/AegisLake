"""Build fresh Delta datasets and the dbt demo warehouse from a card fixture."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import duckdb

from aegis_lakehouse.card_events import SOURCES, select_versions, timestamp
from aegis_lakehouse.card_reconciliation import assess_card_payments
from aegis_lakehouse.spark_session import create_aegis_spark_session

REPO = Path(__file__).resolve().parents[1]
COMMON = "authorization_id STRING, event_id STRING, event_version LONG"
SCHEMAS = {
    "authorizations": COMMON + ", authorized_at STRING, amount_minor LONG, currency STRING,"
    " customer_id STRING, merchant_id STRING, merchant_mcc STRING, status STRING",
    "settlements": COMMON + ", settled_at STRING, settled_amount_minor LONG, settled_currency STRING, fee_minor LONG",
    "ledger": COMMON + ", posted_at STRING, ledger_amount_minor LONG, currency STRING, entry_type STRING",
    "quarantine": "source STRING, event_id STRING, payload STRING, reason STRING",
    "customers": "customer_id STRING, customer_name STRING, kyc_tier STRING, risk_score INT, valid_from STRING",
    "merchants": "merchant_id STRING, merchant_name STRING, mcc STRING, country_code STRING",
    "bronze": "source STRING, payload STRING",
}


def deliver_bronze(spark, fixture, directory, checkpoint_dir):
    """Persist raw envelopes and read them back for the current assessment."""
    envelopes = [{"source": source, "payload": json.dumps(row)}
                 for source in SOURCES for row in fixture[source]]
    payload = "".join(json.dumps(row) + "\n" for row in envelopes)
    if checkpoint_dir is None:
        file_path = directory / "bronze.jsonl"
        file_path.write_text(payload, encoding="utf-8")
        bronze = directory / "lakehouse" / "bronze_events"
        spark.read.schema(SCHEMAS["bronze"]).json(file_path.as_uri()).write.format("delta").save(bronze.as_uri())
    else:
        inbox = checkpoint_dir / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        delivery = checkpoint_dir / f"{uuid4().hex}.jsonl"
        delivery.write_text(payload, encoding="utf-8")
        delivery.replace(inbox / delivery.name)
        bronze = checkpoint_dir / "bronze_events"
        query = (
            spark.readStream.schema(SCHEMAS["bronze"]).json(inbox.as_uri()).writeStream
            .format("delta")
            .option("checkpointLocation", (checkpoint_dir / "checkpoint").as_uri())
            .trigger(availableNow=True)
            .start(bronze.as_uri())
        )
        query.awaitTermination()
    delivered = {source: [] for source in SOURCES}
    for record in spark.read.format("delta").load(bronze.as_uri()).toLocalIterator():
        delivered[record.source].append(json.loads(record.payload))
    return delivered


def build_silver(fixture, directory, checkpoint_dir=None):
    as_of = timestamp(fixture.get("as_of"))
    grace = fixture.get("settlement_grace_minutes")
    if as_of is None or type(grace) is not int or grace < 0:
        raise ValueError("Fixture requires an offset-aware as_of time and a nonnegative whole-minute grace period")
    inputs = directory / "input"
    inputs.mkdir()
    lake = directory / "lakehouse"
    spark = create_aegis_spark_session("AegisLake card demo", warehouse_dir=(directory / "spark").as_uri())
    spark.conf.set("spark.sql.session.timeZone", "UTC")

    def frame(name, rows):
        path = inputs / f"{name}.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return spark.read.schema(SCHEMAS[name]).json(path.as_uri())

    def save(data, name):
        data.write.format("delta").save((lake / name).as_uri())

    try:
        delivered = deliver_bronze(spark, fixture, directory, checkpoint_dir)
        current, quarantine = select_versions(delivered, as_of)
        save(frame("quarantine", quarantine), "quarantine")
        save(frame("customers", fixture["customers"]), "customers")
        save(frame("merchants", fixture["merchants"]), "merchants")
        auth, settlements, ledger = [frame(source, rows) for source, rows in current.items()]
        save(auth, "silver_authorizations")
        save(assess_card_payments(auth, settlements, ledger, as_of, grace), "silver_reconciliation_breaks")
    finally:
        spark.stop()
    return lake


def check_expected(warehouse, expected):
    with duckdb.connect(str(warehouse), read_only=True) as db:
        cases = db.execute("""
            SELECT authorization_id, reconciliation_status, discrepancy_amount_minor, ledger_discrepancy_minor
            FROM fact_reconciliation_breaks
        """).fetchall()
        actual = {key: {"status": status, "settlement_delta": sd, "ledger_delta": ld}
                  for key, status, sd, ld in cases}
        assert len(actual) == len(cases) and actual == expected["cases"], actual
        unknown = db.execute("""
            SELECT authorization_id FROM fact_card_authorizations WHERE merchant_key IS NULL ORDER BY 1
        """).fetchall()
        assert [row[0] for row in unknown] == expected["unknown_merchants"], unknown
        known = db.execute("""
            SELECT count(*) FROM fact_card_authorizations a
            JOIN dim_merchants m ON a.merchant_key = m.merchant_key
            JOIN dim_customers c ON a.customer_key = c.customer_key
            WHERE m.merchant_id = 'merchant_demo' AND c.customer_id = 'cust_demo'
        """).fetchone()[0]
        total = db.execute("SELECT count(*) FROM fact_card_authorizations").fetchone()[0]
        assert known == total - len(unknown), (known, total)
        quarantined = db.execute("SELECT event_id, reason FROM stg_quarantine ORDER BY event_id, reason").fetchall()
        assert quarantined == sorted((row["event_id"], row["reason"]) for row in expected["quarantine"]), quarantined
    print(f"Verified {len(cases)} case outcomes, dimension identities and quarantine")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=REPO / "fixtures/card_demo.json")
    parser.add_argument("--output", type=Path, required=True, help="Fresh output directory")
    parser.add_argument("--expected", type=Path, help="Check Gold against independently specified results")
    parser.add_argument("--checkpoint-dir", type=Path, help="Use a persistent file inbox and Bronze checkpoint")
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    checkpoint_dir = args.checkpoint_dir.resolve() if args.checkpoint_dir else None
    lake = build_silver(fixture, directory, checkpoint_dir)
    warehouse = directory / "aegislake.duckdb"
    project = REPO / "aegis_dbt"
    env = os.environ | {
        "AEGIS_LAKEHOUSE": lake.as_uri(),
        "AEGIS_WAREHOUSE": str(warehouse),
        "DBT_LOG_PATH": str(directory / "dbt_logs"),
    }
    subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", "build", "--project-dir", str(project),
         "--profiles-dir", str(project), "--target-path", str(directory / "dbt_target")],
        env=env, check=True,
    )
    if args.expected:
        check_expected(warehouse, json.loads(args.expected.read_text(encoding="utf-8")))
    print(f"Built {warehouse}")


if __name__ == "__main__":
    main()
