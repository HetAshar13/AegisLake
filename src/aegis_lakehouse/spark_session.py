"""PySpark & Delta Lake Session Factory for AegisLake.

Configures a lightweight, single-node SparkSession with Delta Lake ACID extensions,
bounded memory allocation (2GB), optimized shuffle partitions (4), and Windows-safe paths.
"""

import os
from pathlib import Path
from typing import Optional

from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip


def get_default_warehouse_dir() -> str:
    """Returns a POSIX-normalized path for the local lakehouse warehouse storage."""
    base_dir = Path(__file__).resolve().parent.parent.parent / "data" / "lakehouse"
    base_dir.mkdir(parents=True, exist_ok=True)
    # Convert Windows backslashes to forward slashes for Spark safety
    return base_dir.as_posix()


def create_aegis_spark_session(
    app_name: str = "AegisLake-Medallion",
    warehouse_dir: Optional[str] = None,
    driver_memory: str = "2g",
    shuffle_partitions: int = 4,
) -> SparkSession:
    """Creates an ACID-enabled SparkSession with Delta Lake 3.2.0 extensions.

    Args:
        app_name: Name of the Spark application.
        warehouse_dir: Local path for Delta Lake storage. Defaults to `data/lakehouse`.
        driver_memory: Memory cap for the JVM driver (e.g. '2g').
        shuffle_partitions: Number of partitions to use when shuffling data.

    Returns:
        SparkSession: Configured active SparkSession with Delta support.
    """
    target_warehouse = warehouse_dir or get_default_warehouse_dir()

    # TODO [YOUR TURN TO CODE]:
    # 1. Initialize `builder = SparkSession.builder.appName(app_name).master("local[*]")`
    # 2. Add the driver memory configuration:
    #    `.config("spark.driver.memory", driver_memory)`
    # 3. Add the shuffle partitions configuration (str(shuffle_partitions)):
    #    `.config("spark.sql.shuffle.partitions", str(shuffle_partitions))`
    # 4. Add the Delta Lake extensions:
    #    `.config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")`
    # 5. Add the DeltaCatalog for the default spark_catalog:
    #    `.config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")`
    # 6. Add the warehouse directory:
    #    `.config("spark.sql.warehouse.dir", target_warehouse)`
    # 7. Wrap the builder using `configure_spark_with_delta_pip(builder).getOrCreate()`
    # 8. Set log level to 'WARN' to reduce terminal noise: `spark.sparkContext.setLogLevel("WARN")`
    # 9. Return the spark instance.

    builder = (
        SparkSession.builder.appName(app_name)
        .master("local[*]")
        .config("spark.driver.memory", driver_memory)
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.warehouse.dir", target_warehouse)
    )

    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark
