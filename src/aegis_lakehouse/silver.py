"""AegisLake Silver Layer Processing Engine.

Implements streaming deduplication, event-time watermarking, ISO-4217 financial
invariant validation, and dual-branch routing (Clean Silver vs. Quarantine DLQ).
"""

from typing import Tuple
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# Supported ISO-4217 currencies and statuses for card authorizations
SUPPORTED_CURRENCIES = ["EUR", "USD", "GBP", "JPY", "BHD"]
SUPPORTED_STATUSES = ["AUTHORIZED", "DECLINED", "PENDING"]


def parse_and_validate_authorizations(df: DataFrame) -> DataFrame:
    """Casts raw Bronze columns to strong financial types and computes validation flags.

    Invariants checked:
    1. amount_minor > 0 (prevents negative/zero charges)
    2. currency in SUPPORTED_CURRENCIES (ISO-4217 adherence)
    3. status in SUPPORTED_STATUSES
    4. authorized_at parses cleanly to TimestampType (not null)

    Args:
        df: Input Bronze DataFrame.

    Returns:
        DataFrame: With added timestamp column 'authorized_at_ts' and boolean 'is_valid'.
    """
    #  [YOUR TURN TO CODE]:
    # 1. Cast 'authorized_at' string to timestamp:
    #    with_ts = df.withColumn("authorized_at_ts", F.to_timestamp(F.col("authorized_at")))
    #
    # 2. Define the boolean condition for validity:
    #    valid_condition = (
    #        (F.col("amount_minor") > 0)
    #        & (F.col("currency").isin(SUPPORTED_CURRENCIES))
    #        & (F.col("status").isin(SUPPORTED_STATUSES))
    #        & (F.col("authorized_at_ts").isNotNull())
    #    )
    #
    # 3. Add the 'is_valid' boolean column:
    #    return with_ts.withColumn("is_valid", valid_condition)
    with_ts = df.withColumn("authorized_at_ts", F.to_timestamp(F.col("authorized_at")))
    
    valid_condition = (
        (F.col("amount_minor") > 0)
        & (F.col("currency").isin(SUPPORTED_CURRENCIES))
        & (F.col("status").isin(SUPPORTED_STATUSES))
        & (F.col("authorized_at_ts").isNotNull())
    )
    return with_ts.withColumn("is_valid", valid_condition)


def route_clean_and_quarantine(validated_df: DataFrame) -> Tuple[DataFrame, DataFrame]:
    """Splits the validated stream into two branches: Clean Silver and Quarantine DLQ.

    Clean branch:
    - Retains only rows where is_valid == True.
    - Replaces 'authorized_at' with 'authorized_at_ts'.
    - Drops intermediate 'is_valid' and 'authorized_at_ts' columns.

    Quarantine branch:
    - Retains only rows where is_valid == False.
    - Appends 'quarantined_at' (current_timestamp()).
    - Appends 'quarantine_reason' (string description).
    """
    #  [YOUR TURN TO CODE]:
    # 1. Build clean_df:
    #    clean_df = (
    #        validated_df.filter(F.col("is_valid") == True)
    #        .withColumn("authorized_at", F.col("authorized_at_ts"))
    #        .drop("authorized_at_ts", "is_valid")
    #    )
    #
    # 2. Build quarantine_df:
    #    quarantine_df = (
    #        validated_df.filter(F.col("is_valid") == False)
    #        .withColumn("quarantined_at", F.current_timestamp())
    #        .withColumn("quarantine_reason", F.lit("FAILED_FINANCIAL_INVARIANT"))
    #        .drop("authorized_at_ts", "is_valid")
    #    )
    #
    # 3. Return (clean_df, quarantine_df)
    clean_df = (
        validated_df.filter(F.col("is_valid") == True)
        .withColumn("authorized_at", F.col("authorized_at_ts"))
        .drop("authorized_at_ts", "is_valid")
    )
    quarantine_df = (
        validated_df.filter(F.col("is_valid") == False)
        .withColumn("quarantined_at", F.current_timestamp())
        .withColumn("quarantine_reason", F.lit("FAILED_FINANCIAL_INVARIANT"))
        .drop("authorized_at_ts", "is_valid")
    )
    return clean_df, quarantine_df  


def apply_watermarked_deduplication(
    clean_df: DataFrame,
    watermark_col: str = "authorized_at",
    watermark_delay: str = "10 minutes",
    dedup_cols: Tuple[str, ...] = ("authorization_id",),
) -> DataFrame:
    """Applies event-time watermarking and drops duplicate records within the bounded window.

    Why Watermarking is Mandatory in Streaming:
    Without a watermark, PySpark's state store (RocksDB/HDFS) must remember every
    seen key forever, leading to unbounded memory growth and Out-Of-Memory (OOM) crashes.
    The watermark bounds state memory to the watermark threshold.
    """
    #  [YOUR TURN TO CODE]:
    # return (
    #     clean_df
    #     .withWatermark(watermark_col, watermark_delay)
    #     .dropDuplicates(list(dedup_cols))
    # )
    return (
        clean_df
        .withWatermark(watermark_col, watermark_delay)
        .dropDuplicates(list(dedup_cols))
    )
