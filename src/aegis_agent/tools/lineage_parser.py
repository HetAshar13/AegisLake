"""
AegisLake Module 4: Deterministic Column-Level Lineage Parser
Uses SQLglot 30+ AST lineage graph extraction for DuckDB dbt models.
"""

from typing import Dict, Any, List, Optional
import sqlglot
from sqlglot import exp
from sqlglot.lineage import lineage


def extract_column_lineage(
    sql_query: str,
    target_column: str,
    dialect: str = "duckdb",
    schema: Optional[Dict[str, Dict[str, str]]] = None,
    sources: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Parses a SQL model and extracts column-level lineage for a target column,
    tracing expressions, upstream source columns, and referenced tables/CTEs.

    Args:
        sql_query (str): The SQL SELECT statement or dbt model query.
        target_column (str): The column name to trace upstream.
        dialect (str): The SQL dialect (default 'duckdb').
        schema (dict): Optional schema definitions for root tables.
        sources (dict): Optional mapping of upstream table names to their queries.

    Returns:
        dict: Inspectable lineage dictionary containing:
              - "target_column": str
              - "source_columns": List[str] (sorted)
              - "upstream_tables": List[str] (sorted)
              - "expression": Optional[str]
              - "expression_history": List[str]
              - "status": "SUCCESS" or "FAILED"
              - "error_message": Optional[str] (on failure)

     Implement the lineage extraction logic:
    1. Initialize schema and sources to empty dicts if None.
    2. In a try block:
       a. Call `sqlglot.lineage.lineage(...)` with column, sql, dialect, schema, sources.
          This returns a root Lineage `Node` object representing the column's AST graph.
       b. Initialize two empty sets: `source_columns = set()` and `upstream_tables = set()`,
          and a list `expressions = []`.
       c. Iterate over each node `n` in `node.walk()`:
          - If `n.expression`: append `n.expression.sql(dialect=dialect)` to `expressions`.
          - If `hasattr(n, "source") and n.source`:
            - For each col in `n.source.find_all(exp.Column)`: add `col.name` to `source_columns`.
            - For each tbl in `n.source.find_all(exp.Table)`: add `tbl.name` to `upstream_tables`.
       d. Discard `target_column` itself from `source_columns` (we want root source columns, not the target itself).
       e. Return the dictionary with status="SUCCESS", sorted lists of columns and tables,
          and `node.expression.sql(dialect=dialect)` as the primary expression.
    3. In an except Exception as e block:
       Return a dictionary with status="FAILED", empty lists for columns/tables,
       and "error_message": str(e).
    """
    if schema is None:
        schema = {}
    if sources is None:
        sources = {}

    try:
        node = lineage(
            column=target_column,
            sql=sql_query,
            dialect=dialect,
            schema=schema,
            sources=sources,
        )

        source_columns = set()
        upstream_tables = set()
        expressions = []

        for n in node.walk():
            if n.expression:
                expressions.append(n.expression.sql(dialect=dialect))
            if hasattr(n, "source") and n.source:
                for col in n.source.find_all(exp.Column):
                    source_columns.add(col.name)
                for tbl in n.source.find_all(exp.Table):
                    upstream_tables.add(tbl.name)

        # Discard the target column itself from source columns
        source_columns.discard(target_column)

        return {
            "target_column": target_column,
            "source_columns": sorted(source_columns),
            "upstream_tables": sorted(upstream_tables),
            "expression": node.expression.sql(dialect=dialect) if node.expression else None,
            "expression_history": expressions,
            "status": "SUCCESS",
            "error_message": None,
        }

    except Exception as e:
        return {
            "target_column": target_column,
            "source_columns": [],
            "upstream_tables": [],
            "expression": None,
            "expression_history": [],
            "status": "FAILED",
            "error_message": str(e),
        }
