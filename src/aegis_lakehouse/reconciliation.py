"""AegisLake Multi-Rail Three-Way Financial Reconciliation Engine.

Performs deterministic Three-Way Matching across:
1. Internal Authorizations (`silver_card_authorizations`)
2. External Clearinghouse Settlements (`clearinghouse_settlements`)
3. Bank General Ledger (`general_ledger_entries`)

Identifies and classifies reconciliation breaks (unmatched auths, orphan settlements,
amount variances, currency mismatches) and persists results using Delta Lake MERGE INTO.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from delta.tables import DeltaTable


def run_three_way_reconciliation(
    auth_df: DataFrame,
    settlement_df: DataFrame,
    ledger_df: DataFrame,
) -> DataFrame:
    """Executes Three-Way full outer join and classifies reconciliation breaks.

    Break Classification Taxonomy:
    - 'BREAK_UNMATCHED_AUTHORIZATION': Authorized internally, but missing clearinghouse settlement.
    - 'BREAK_UNMATCHED_SETTLEMENT': Settlement exists, but no internal authorization found.
    - 'BREAK_CURRENCY_MISMATCH': Authorization and settlement currencies disagree.
    - 'BREAK_AMOUNT_MISMATCH': Authorization and settlement amounts differ.
    - 'MATCHED': All rails align on identifier, currency, and minor-unit amounts.

    Args:
        auth_df: Internal authorizations DataFrame.
        settlement_df: Clearinghouse settlement reports DataFrame.
        ledger_df: Bank general ledger entries DataFrame.

    Returns:
        DataFrame: Unified reconciliation results with 'reconciliation_status' and discrepancy metrics.
    """
    # Rename columns to avoid ambiguity during full outer join
    a = auth_df.select(
        F.col("authorization_id").alias("auth_id"),
        F.col("amount_minor").alias("auth_amount"),
        F.col("currency").alias("auth_currency"),
    )
    s = settlement_df.select(
        F.col("authorization_id").alias("settle_id"),
        F.col("settled_amount_minor").alias("settle_amount"),
        F.col("settled_currency").alias("settle_currency"),
    )
    l = ledger_df.select(
        F.col("authorization_id").alias("ledger_id"),
        F.col("ledger_amount_minor").alias("ledger_amount"),
    )

    #  [YOUR TURN TO CODE]:
    # 1. Perform full outer join across the three rails on authorization_id:
    #    joined_df = a.join(s, a["auth_id"] == s["settle_id"], "full").join(
    #        l, F.coalesce(a["auth_id"], s["settle_id"]) == l["ledger_id"], "full"
    #    )
    #
    # 2. Coalesce the primary authorization_id:
    #    with_id = joined_df.withColumn(
    #        "authorization_id", F.coalesce(F.col("auth_id"), F.col("settle_id"), F.col("ledger_id"))
    #    )
    #
    # 3. Define the break classification logic using F.when() / F.otherwise():
    #    status_col = (
    #        F.when(F.col("auth_id").isNotNull() & F.col("settle_id").isNull(), "BREAK_UNMATCHED_AUTHORIZATION")
    #        .when(F.col("auth_id").isNull() & F.col("settle_id").isNotNull(), "BREAK_UNMATCHED_SETTLEMENT")
    #        .when(F.col("auth_currency") != F.col("settle_currency"), "BREAK_CURRENCY_MISMATCH")
    #        .when(F.col("auth_amount") != F.col("settle_amount"), "BREAK_AMOUNT_MISMATCH")
    #        .otherwise("MATCHED")
    #    )
    #
    # 4. Add 'reconciliation_status', 'discrepancy_amount', and 'reconciled_at':
    #    reconciled = (
    #        with_id
    #        .withColumn("reconciliation_status", status_col)
    #        .withColumn(
    #            "discrepancy_amount",
    #            F.coalesce(F.col("settle_amount"), F.lit(0)) - F.coalesce(F.col("auth_amount"), F.lit(0))
    #        )
    #        .withColumn("reconciled_at", F.current_timestamp())
    #        .select(
    #            "authorization_id",
    #            F.col("auth_amount").alias("auth_amount_minor"),
    #            F.col("settle_amount").alias("settled_amount_minor"),
    #            F.coalesce(F.col("auth_currency"), F.col("settle_currency")).alias("currency"),
    #            "reconciliation_status",
    #            "discrepancy_amount",
    #            "reconciled_at",
    #        )
    #    )
    #    return reconciled
    joined_df = a.join(s, a["auth_id"] == s["settle_id"], "full").join(
        l, F.coalesce(a["auth_id"], s["settle_id"]) == l["ledger_id"], "full"
    )
    with_id = joined_df.withColumn(
        "authorization_id", F.coalesce(F.col("auth_id"), F.col("settle_id"), F.col("ledger_id"))
    )
    status_col = (
        F.when(F.col("auth_id").isNotNull() & F.col("settle_id").isNull(), "BREAK_UNMATCHED_AUTHORIZATION")
        .when(F.col("auth_id").isNull() & F.col("settle_id").isNotNull(), "BREAK_UNMATCHED_SETTLEMENT")
        .when(F.col("auth_currency") != F.col("settle_currency"), "BREAK_CURRENCY_MISMATCH")
        .when(F.col("auth_amount") != F.col("settle_amount"), "BREAK_AMOUNT_MISMATCH")
        .otherwise("MATCHED")
    )
    reconciled = (
        with_id
        .withColumn("reconciliation_status", status_col)
        .withColumn(
            "discrepancy_amount",
            F.coalesce(F.col("settle_amount"), F.lit(0)) - F.coalesce(F.col("auth_amount"), F.lit(0))
        )
        .withColumn("reconciled_at", F.current_timestamp())
        .select(
            "authorization_id",
            F.col("auth_amount").alias("auth_amount_minor"),
            F.col("settle_amount").alias("settled_amount_minor"),
            F.coalesce(F.col("auth_currency"), F.col("settle_currency")).alias("currency"),
            "reconciliation_status",
            "discrepancy_amount",
            "reconciled_at",
        )
    )
    return reconciled       

def upsert_reconciliation_breaks(
    spark: SparkSession,
    breaks_df: DataFrame,
    target_table_path: str,
) -> None:
    """Executes a Delta Lake MERGE INTO upsert into the fact_reconciliation_breaks table.

    Updates existing breaks (e.g. from UNMATCHED to MATCHED when late settlements arrive)
    and inserts new records atomically.

    Args:
        spark: Active SparkSession.
        breaks_df: Reconciled breaks DataFrame to upsert.
        target_table_path: Path to target Delta Lake table.
    """
    #  [YOUR TURN TO CODE]:
    # delta_table = DeltaTable.forPath(spark, target_table_path)
    # (
    #     delta_table.alias("target")
    #     .merge(
    #         breaks_df.alias("source"),
    #         "target.authorization_id = source.authorization_id"
    #     )
    #     .whenMatchedUpdateAll()
    #     .whenNotMatchedInsertAll()
    #     .execute()
    # )
    delta_table = DeltaTable.forPath(spark, target_table_path)
    (
        delta_table.alias("target")
        .merge(
            breaks_df.alias("source"),
            "target.authorization_id = source.authorization_id"
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )   
