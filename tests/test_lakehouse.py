"""Tests for AegisLake Spark Session & Delta Lake Foundation.
"""

import json
import shutil
from pathlib import Path
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import LongType, StringType

from aegis_lakehouse.spark_session import create_aegis_spark_session
from aegis_lakehouse.bronze import (
    get_card_authorization_bronze_schema,
    ingest_raw_events_to_bronze,
)
from aegis_lakehouse.silver import (
    parse_and_validate_authorizations,
    route_clean_and_quarantine,
    apply_watermarked_deduplication,
)
from aegis_lakehouse.delta_optimization import (
    enable_change_data_feed,
    read_silver_change_feed,
    optimize_and_compact_table,
)
from aegis_lakehouse.reconciliation import (
    run_three_way_reconciliation,
    upsert_reconciliation_breaks,
)


@pytest.fixture(scope="session")
def spark_session():
    """Initializes a shared SparkSession for test execution."""
    spark = create_aegis_spark_session(
        app_name="AegisLake-UnitTests",
        shuffle_partitions=2,
    )
    yield spark
    spark.stop()


class TestSparkSessionConfiguration:
    """Verifies that PySpark and Delta Lake 3.2.0 are properly configured."""

    def test_spark_session_initializes(self, spark_session: SparkSession):
        assert spark_session is not None
        assert spark_session.version.startswith("3.5")

    def test_shuffle_partitions_optimized(self, spark_session: SparkSession):
        # Must be 2 (from fixture) or 4, NOT the default 200
        partitions = spark_session.conf.get("spark.sql.shuffle.partitions")
        assert partitions in ["2", "4"]

    def test_delta_catalog_registered(self, spark_session: SparkSession):
        catalog = spark_session.conf.get("spark.sql.catalog.spark_catalog")
        assert catalog == "org.apache.spark.sql.delta.catalog.DeltaCatalog"

    def test_delta_lake_table_acid_write_and_read(self, spark_session: SparkSession, tmp_path: Path):
        test_delta_dir = (tmp_path / "delta_test_table").as_posix()

        # Create a sample financial test DataFrame via Catalyst engine (Windows socket-free)
        df = spark_session.sql("""
            SELECT 'auth_001' AS authorization_id, 'EUR' AS currency, 1999L AS amount_minor, 'cust_01' AS customer_id
            UNION ALL SELECT 'auth_002', 'USD', 2500L, 'cust_02'
            UNION ALL SELECT 'auth_003', 'JPY', 5000L, 'cust_03'
        """)

        # Write as ACID Delta Table
        df.write.format("delta").mode("overwrite").save(test_delta_dir)

        # Verify Delta commit log was created on disk
        delta_log_dir = Path(test_delta_dir) / "_delta_log"
        assert delta_log_dir.exists(), "The _delta_log transaction directory must exist"
        assert any(delta_log_dir.glob("*.json")), "At least one commit JSON file must be present"

        # Read back using Delta reader
        read_df = spark_session.read.format("delta").load(test_delta_dir)
        assert read_df.count() == 3
        expected_cols = {"authorization_id", "currency", "amount_minor", "customer_id"}
        assert set(read_df.columns) == expected_cols


class TestBronzeLayerIngestion:
    """Verifies the Bronze layer streaming ingestion, schema validation, and audit metadata."""

    def test_bronze_schema_structure(self):
        schema = get_card_authorization_bronze_schema()
        assert schema is not None
        field_names = [f.name for f in schema.fields]
        assert "authorization_id" in field_names
        assert "amount_minor" in field_names
        assert "currency" in field_names
        assert "customer_id" in field_names
        assert "status" in field_names
        
        # Verify amount_minor is strictly LongType (financial integer minor units)
        amount_field = next(f for f in schema.fields if f.name == "amount_minor")
        assert isinstance(amount_field.dataType, LongType)

    def test_bronze_streaming_ingestion(self, spark_session: SparkSession, tmp_path: Path):
        source_dir = tmp_path / "raw_events_landing"
        source_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_dir = (tmp_path / "checkpoints_bronze").as_posix()
        bronze_table_dir = (tmp_path / "delta_bronze").as_posix()

        # Generate sample raw JSON event files landing in source directory
        raw_events = [
            {
                "event_id": "evt_001",
                "authorization_id": "auth_101",
                "idempotency_key": "idemp_101",
                "customer_id": "cust_101",
                "merchant_id": "merch_101",
                "payment_rail": "CARD",
                "amount_minor": 4999,
                "currency": "EUR",
                "card_last4": "1234",
                "status": "AUTHORIZED",
                "authorized_at": "2026-11-04T00:00:00Z",
                "merchant_mcc": "5411",
            },
            {
                "event_id": "evt_002",
                "authorization_id": "auth_102",
                "idempotency_key": "idemp_102",
                "customer_id": "cust_102",
                "merchant_id": "merch_102",
                "payment_rail": "CARD",
                "amount_minor": 10500,
                "currency": "USD",
                "card_last4": "5678",
                "status": "AUTHORIZED",
                "authorized_at": "2026-11-04T00:01:00Z",
                "merchant_mcc": "5812",
            },
        ]
        
        event_file = source_dir / "batch_01.json"
        with open(event_file, "w") as f:
            for ev in raw_events:
                f.write(json.dumps(ev) + "\n")

        # Ingest stream via availableNow
        query = ingest_raw_events_to_bronze(
            spark=spark_session,
            source_dir=str(source_dir),
            checkpoint_dir=checkpoint_dir,
            target_delta_dir=bronze_table_dir,
            available_now=True,
        )

        # Verify Delta table and checkpoint directory creation
        delta_log = Path(bronze_table_dir) / "_delta_log"
        assert delta_log.exists()
        
        # Verify records and audit columns in Bronze Delta table
        bronze_df = spark_session.read.format("delta").load(bronze_table_dir)
        assert bronze_df.count() == 2
        
        cols = bronze_df.columns
        assert "ingested_at" in cols
        assert "source_file" in cols
        assert "authorization_id" in cols
        
        currencies = [row.currency for row in bronze_df.select("currency").collect()]
        assert set(currencies) == {"EUR", "USD"}


class TestSilverLayerProcessing:
    """Verifies Silver layer validation, dual-branch quarantine routing, and deduplication."""

    def test_silver_validation_and_quarantine_split(self, spark_session: SparkSession):
        raw_bronze_df = spark_session.sql("""
            SELECT 'evt_1' AS event_id, 'auth_1' AS authorization_id, 1000L AS amount_minor, 'EUR' AS currency, 'AUTHORIZED' AS status, '2026-11-04T00:00:00Z' AS authorized_at
            UNION ALL SELECT 'evt_2', 'auth_2', 2500L, 'USD', 'AUTHORIZED', '2026-11-04T00:01:00Z'
            UNION ALL SELECT 'evt_3', 'auth_3', 3000L, 'XYZ', 'AUTHORIZED', '2026-11-04T00:02:00Z' -- INVALID CURRENCY
            UNION ALL SELECT 'evt_4', 'auth_4', -500L, 'EUR', 'AUTHORIZED', '2026-11-04T00:03:00Z' -- NEGATIVE AMOUNT
        """)

        validated_df = parse_and_validate_authorizations(raw_bronze_df)
        clean_df, quarantine_df = route_clean_and_quarantine(validated_df)

        # 2 Clean records, 2 Quarantined records
        assert clean_df.count() == 2
        assert quarantine_df.count() == 2

        # Verify quarantine metadata columns
        q_cols = quarantine_df.columns
        assert "quarantined_at" in q_cols
        assert "quarantine_reason" in q_cols

        # Verify clean records have correct currencies
        clean_currencies = {row.currency for row in clean_df.select("currency").collect()}
        assert clean_currencies == {"EUR", "USD"}

    def test_silver_deduplication(self, spark_session: SparkSession):
        duplicates_df = spark_session.sql("""
            SELECT 'evt_1' AS event_id, 'auth_dup_1' AS authorization_id, 1000L AS amount_minor, 'EUR' AS currency, 'AUTHORIZED' AS status, CAST('2026-11-04T00:00:00Z' AS TIMESTAMP) AS authorized_at
            UNION ALL SELECT 'evt_2', 'auth_dup_1', 1000L, 'EUR', 'AUTHORIZED', CAST('2026-11-04T00:00:00Z' AS TIMESTAMP)
            UNION ALL SELECT 'evt_3', 'auth_uniq_2', 2000L, 'USD', 'AUTHORIZED', CAST('2026-11-04T00:05:00Z' AS TIMESTAMP)
        """)

        dedup_df = apply_watermarked_deduplication(duplicates_df)
        assert dedup_df.count() == 2


class TestDeltaLakeOptimizationAndCDF:
    """Verifies Delta Lake Change Data Feed (CDF) tracking and table optimization."""

    def test_enable_and_read_change_data_feed(self, spark_session: SparkSession, tmp_path: Path):
        table_dir = (tmp_path / "delta_cdf_test").as_posix()

        # Step 1: Create initial Delta table
        initial_df = spark_session.sql("""
            SELECT 'auth_1' AS authorization_id, 1000L AS amount_minor, 'EUR' AS currency, 'AUTHORIZED' AS status
            UNION ALL SELECT 'auth_2', 2000L, 'USD', 'AUTHORIZED'
        """)
        initial_df.write.format("delta").mode("overwrite").save(table_dir)

        # Step 2: Enable Change Data Feed
        enable_change_data_feed(spark_session, table_dir)

        # Step 3: Append new record (Version 2)
        new_record_df = spark_session.sql("""
            SELECT 'auth_3' AS authorization_id, 3000L AS amount_minor, 'GBP' AS currency, 'AUTHORIZED' AS status
        """)
        new_record_df.write.format("delta").mode("append").save(table_dir)

        # Step 4: Read Change Data Feed starting from Version 2
        cdf_df = read_silver_change_feed(spark_session, table_dir, starting_version=2)

        # Verify CDF changelog metadata columns exist
        cols = cdf_df.columns
        assert "_change_type" in cols
        assert "_commit_version" in cols
        assert "_commit_timestamp" in cols

        # Verify the inserted record
        assert cdf_df.count() == 1
        row = cdf_df.collect()[0]
        assert row["_change_type"] == "insert"
        assert row["authorization_id"] == "auth_3"
        assert row["_commit_version"] == 2

    def test_optimize_and_compact_table(self, spark_session: SparkSession, tmp_path: Path):
        table_dir = (tmp_path / "delta_optimize_test").as_posix()

        # Write multiple small batches to simulate streaming micro-batches
        for i in range(3):
            batch_df = spark_session.sql(f"""
                SELECT 'auth_{i}' AS authorization_id, 1500L AS amount_minor, 'EUR' AS currency
            """)
            batch_df.write.format("delta").mode("append").save(table_dir)

        # Run optimize and compaction with Z-Ordering
        metrics_df = optimize_and_compact_table(spark_session, table_dir, zorder_col="authorization_id")
        assert metrics_df is not None

        # Verify optimization metrics returned
        metrics_row = metrics_df.collect()[0]
        assert hasattr(metrics_row, "metrics") or "metrics" in metrics_row or "numFilesAdded" in str(metrics_row)


class TestMultiRailReconciliation:
    """Verifies Three-Way Reconciliation matching logic, break taxonomy, and Delta MERGE."""

    def test_three_way_reconciliation_matching(self, spark_session: SparkSession):
        # 1. Authorizations
        auth_df = spark_session.sql("""
            SELECT 'auth_1' AS authorization_id, 1000L AS amount_minor, 'EUR' AS currency
            UNION ALL SELECT 'auth_2', 2000L, 'USD' -- Missing settlement
            UNION ALL SELECT 'auth_4', 1500L, 'EUR' -- Amount mismatch
            UNION ALL SELECT 'auth_5', 3000L, 'EUR' -- Currency mismatch
        """)

        # 2. Settlements
        settle_df = spark_session.sql("""
            SELECT 'auth_1' AS authorization_id, 1000L AS settled_amount_minor, 'EUR' AS settled_currency
            UNION ALL SELECT 'auth_3', 5000L, 'GBP' -- Orphan settlement (no auth)
            UNION ALL SELECT 'auth_4', 1800L, 'EUR' -- Amount mismatch (settled 1800 vs auth 1500)
            UNION ALL SELECT 'auth_5', 3000L, 'USD' -- Currency mismatch (settled USD vs auth EUR)
        """)

        # 3. Ledger
        ledger_df = spark_session.sql("""
            SELECT 'auth_1' AS authorization_id, 1000L AS ledger_amount_minor
            UNION ALL SELECT 'auth_2', 2000L
            UNION ALL SELECT 'auth_4', 1800L
        """)

        reconciled_df = run_three_way_reconciliation(auth_df, settle_df, ledger_df)
        assert reconciled_df.count() == 5

        # Collect break statuses by authorization_id
        statuses = {
            row["authorization_id"]: row["reconciliation_status"]
            for row in reconciled_df.collect()
        }

        assert statuses["auth_1"] == "MATCHED"
        assert statuses["auth_2"] == "BREAK_UNMATCHED_AUTHORIZATION"
        assert statuses["auth_3"] == "BREAK_UNMATCHED_SETTLEMENT"
        assert statuses["auth_4"] == "BREAK_AMOUNT_MISMATCH"
        assert statuses["auth_5"] == "BREAK_CURRENCY_MISMATCH"

        # Verify discrepancy calculation on amount mismatch
        row_4 = next(r for r in reconciled_df.collect() if r["authorization_id"] == "auth_4")
        assert row_4["discrepancy_amount"] == 300

    def test_upsert_reconciliation_breaks_merge(self, spark_session: SparkSession, tmp_path: Path):
        breaks_dir = (tmp_path / "delta_breaks_table").as_posix()

        # Initial break table with an unmatched authorization
        initial_df = spark_session.sql("""
            SELECT 'auth_2' AS authorization_id, 2000L AS auth_amount_minor, CAST(NULL AS BIGINT) AS settled_amount_minor, 'USD' AS currency, 'BREAK_UNMATCHED_AUTHORIZATION' AS reconciliation_status, -2000L AS discrepancy_amount, CURRENT_TIMESTAMP() AS reconciled_at
        """)
        initial_df.write.format("delta").mode("overwrite").save(breaks_dir)

        # Updated record: settlement arrived late, now MATCHED
        updated_df = spark_session.sql("""
            SELECT 'auth_2' AS authorization_id, 2000L AS auth_amount_minor, 2000L AS settled_amount_minor, 'USD' AS currency, 'MATCHED' AS reconciliation_status, 0L AS discrepancy_amount, CURRENT_TIMESTAMP() AS reconciled_at
        """)

        # Execute Delta MERGE INTO
        upsert_reconciliation_breaks(spark_session, updated_df, breaks_dir)

        # Read back and verify update in place (no duplicate row, status updated)
        result_df = spark_session.read.format("delta").load(breaks_dir)
        assert result_df.count() == 1
        updated_row = result_df.collect()[0]
        assert updated_row["reconciliation_status"] == "MATCHED"
        assert updated_row["settled_amount_minor"] == 2000
