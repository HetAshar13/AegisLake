"""
AegisLake Power BI Exporter
Exports DuckDB Gold Marts and Dimensions to Parquet & CSV for Power BI Desktop ingestion.
"""

import os
import sys
import duckdb
from pathlib import Path

# UTF-8 stdout encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = "aegis_dbt/aegislake_warehouse.duckdb"
OUTPUT_DIR = Path("aegis_bi/data")

def main():
    print("=" * 65)
    print("📊 AegisLake: Exporting Power BI Semantic Dataset")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(DB_PATH, read_only=True)

    tables = [
        "fact_card_authorizations",
        "fact_reconciliation_breaks",
        "dim_currencies",
        "dim_merchants",
        "dim_customers",
    ]

    for table in tables:
        parquet_path = OUTPUT_DIR / f"{table}.parquet"
        csv_path = OUTPUT_DIR / f"{table}.csv"

        # Export to Parquet (High performance columnar)
        conn.execute(f"COPY {table} TO '{parquet_path.as_posix()}' (FORMAT PARQUET);")
        # Export to CSV (Human readable / Excel / Power BI text)
        conn.execute(f"COPY {table} TO '{csv_path.as_posix()}' (FORMAT CSV, HEADER);")

        row_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"✅ Exported {table:30s} -> {row_count:5d} rows (Parquet & CSV)")

    # Also export all tables into a unified multi-sheet Excel workbook for 1-click Power BI import
    excel_path = OUTPUT_DIR / "aegislake_semantic_model.xlsx"
    import pandas as pd
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for table in tables:
            df = conn.execute(f"SELECT * FROM {table}").df()
            # Convert timezone-aware datetimes to timezone-naive (Excel requirement)
            for col in df.select_dtypes(include=["datetimetz"]).columns:
                df[col] = df[col].dt.tz_localize(None)
            sheet_name = table[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"📦 Created unified Excel Workbook: {excel_path.resolve()} (All 5 sheets included)")

    print("-" * 65)
    print(f"📁 Dataset files saved to: {OUTPUT_DIR.resolve()}")
    print("=" * 65)

if __name__ == "__main__":
    main()
