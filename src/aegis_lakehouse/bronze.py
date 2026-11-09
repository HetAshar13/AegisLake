"""AegisLake Bronze Layer Ingestion Engine.

Implements raw, immutable streaming ingestion into Delta Lake with audit metadata
and checkpoint recovery, conforming to BCBS 239 / SOX financial compliance rules.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, input_file_name
from pyspark.sql.streaming import StreamingQuery
from pyspark.sql.types import (
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


def get_card_authorization_bronze_schema() -> StructType:
    """Returns the explicit StructType schema for Card Authorization raw events.

    In production financial lakehouses, schema-on-read must be strictly defined
    to avoid silent type coercion or schema drift.
    """
    # TODO [YOUR TURN TO CODE]:
    # Return a StructType containing the following StructField fields (all nullable=True):
    # 1. "event_id": StringType()
    # 2. "authorization_id": StringType()
    # 3. "idempotency_key": StringType()
    # 4. "customer_id": StringType()
    # 5. "merchant_id": StringType()
    # 6. "payment_rail": StringType()
    # 7. "amount_minor": LongType()
    # 8. "currency": StringType()
    # 9. "card_last4": StringType()
    # 10. "status": StringType()
    # 11. "authorized_at": StringType()
    # 12. "merchant_mcc": StringType()
    return StructType([
        StructField("event_id", StringType(), nullable=True),
        StructField("authorization_id", StringType(), nullable=True),
        StructField("idempotency_key", StringType(), nullable=True),
        StructField("customer_id", StringType(), nullable=True),
        StructField("merchant_id", StringType(), nullable=True),
        StructField("payment_rail", StringType(), nullable=True),
        StructField("amount_minor", LongType(), nullable=True),
        StructField("currency", StringType(), nullable=True),
        StructField("card_last4", StringType(), nullable=True),
        StructField("status", StringType(), nullable=True),
        StructField("authorized_at", StringType(), nullable=True),
        StructField("merchant_mcc", StringType(), nullable=True)
    ])
   


def ingest_raw_events_to_bronze(
    spark: SparkSession,
    source_dir: str,    
    checkpoint_dir: str,
    target_delta_dir: str,
    available_now: bool = True,
) -> StreamingQuery:
    """Ingests raw event JSON streams into the Bronze Delta table.

    Audit Invariants:
    1. Schema Preservation: Raw payload fields are preserved as ingested.
    2. Audit Lineage: Appends 'ingested_at' (current_timestamp()) and 'source_file' (input_file_name()).
    3. Exactly-Once / Idempotence: Enforced by Delta Lake transaction log and checkpoint state.
    4. Never Drop Data: Bronze must ingest all records without filtering or dropping.

    Args:
        spark: Active SparkSession.
        source_dir: Path to directory containing raw JSON files.
        checkpoint_dir: Path to write Structured Streaming checkpoint state.
        target_delta_dir: Path to write Bronze Delta table.
        available_now: When True, uses trigger(availableNow=True) to process all
                       available data incrementally and terminate.

    Returns:
        StreamingQuery: Active or completed streaming query handle.
    """
    # TODO [YOUR TURN TO CODE]:
    # 1. Get the bronze schema using `schema = get_card_authorization_bronze_schema()`
    # 2. Read the stream using:
    #    `raw_stream = spark.readStream.schema(schema).json(source_dir)`
    # 3. Add audit lineage metadata columns:
    #    `bronze_df = (raw_stream
    #         .withColumn("ingested_at", current_timestamp())
    #         .withColumn("source_file", input_file_name()))`
    # 4. Configure the writeStream:
    #    `writer = (bronze_df.writeStream
    #         .format("delta")
    #         .outputMode("append")
    #         .option("checkpointLocation", checkpoint_dir))`
    # 5. If `available_now` is True, apply:
    #    `writer = writer.trigger(availableNow=True)`
    # 6. Start the query:
    #    `query = writer.start(target_delta_dir)`
    # 7. If `available_now` is True, call `query.awaitTermination()`
    # 8. Return `query`
    schema = get_card_authorization_bronze_schema()
    raw_stream = spark.readStream.schema(schema).json(source_dir)
    bronze_df = (raw_stream
        .withColumn("ingested_at", current_timestamp())
        .withColumn("source_file", input_file_name()))

    writer = (bronze_df.writeStream
        .format("delta")
        .outputMode("append")
        .option("checkpointLocation", checkpoint_dir))

    if available_now:
        writer = writer.trigger(availableNow=True)
    query = writer.start(target_delta_dir)

    if available_now:
        query.awaitTermination()
        
    return query
