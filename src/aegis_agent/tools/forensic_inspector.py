"""
AegisLake Module 4: Forensic Inspector Tool
Inspects DuckDB tables (`fact_reconciliation_breaks`, `fact_card_authorizations`)
to fetch real reconciliation breaks and forensic transaction details for agent triage.
"""

from typing import Dict, Any, Optional
import duckdb


def fetch_worst_reconciliation_break(
    db_path: str = "aegis_dbt/aegislake_warehouse.duckdb",
) -> Optional[Dict[str, Any]]:
    """
       Fetches the highest absolute discrepancy un-reconciled record from fact_reconciliation_breaks.

       Args:
           db_path (str): Path to the DuckDB database file.

       Returns:
           Optional[Dict[str, Any]]: Dictionary containing the worst break record details, or None.

    Implement the query logic:
       1. Connect to DuckDB with `duckdb.connect(db_path, read_only=True)`.
       2. Write a SQL query to SELECT:
          authorization_id, reconciliation_status, discrepancy_amount_minor,
          discrepancy_amount_scaled, is_actionable_break, reconciled_at
          FROM fact_reconciliation_breaks
          WHERE is_actionable_break = true
          ORDER BY ABS(discrepancy_amount_scaled) DESC
          LIMIT 1;
       3. Execute the query and fetchone().
       4. Extract column names from `[desc[0] for desc in conn.description]`.
       5. Close the connection.
       6. If result is None, return None. Otherwise, return `dict(zip(columns, result))`.
       7. Wrap in try/except to return None on error.
    """
    try:
        conn = duckdb.connect(db_path, read_only=True)
        query = """
            SELECT
                authorization_id,
                reconciliation_status,
                discrepancy_amount_minor,
                discrepancy_amount_scaled,
                is_actionable_break,
                reconciled_at
            FROM fact_reconciliation_breaks
            WHERE is_actionable_break = true
            ORDER BY ABS(discrepancy_amount_scaled) DESC
            LIMIT 1;
        """
        result = conn.execute(query).fetchone()
        columns = [desc[0] for desc in conn.description]
        conn.close()
        if result is None:
            return None
        return dict(zip(columns, result))
    except Exception as e:
        print(f"Error fetching worst reconciliation break: {e}")
        return None


def fetch_break_forensics(
    authorization_id: str,
    db_path: str = "aegis_dbt/aegislake_warehouse.duckdb",
) -> Dict[str, Any]:
    """
     Inspects a specific break record by authorization_id, combining fact_reconciliation_breaks
     and fact_card_authorizations.

     Args:
         authorization_id (str): The specific authorization identifier to inspect.
         db_path (str): Path to the DuckDB database file.

     Returns:
         Dict[str, Any]: Comprehensive forensic breakdown.

    : Implement the forensic query logic:
     1. Connect to DuckDB with `duckdb.connect(db_path, read_only=True)`.
     2. Write a SQL query with parameter placeholder `?`:
        SELECT
            b.authorization_id,
            b.reconciliation_status,
            b.auth_amount_minor,
            b.settled_amount_minor,
            b.discrepancy_amount_minor,
            b.discrepancy_amount_scaled,
            b.is_actionable_break,
            a.merchant_key,
            a.customer_key,
            a.auth_status
        FROM fact_reconciliation_breaks b
        LEFT JOIN fact_card_authorizations a ON b.authorization_id = a.authorization_id
        WHERE b.authorization_id = ?;
     3. Execute query with `[authorization_id]` parameter and fetchone().
     4. Close the connection.
     5. If no record is found, return:
        {"authorization_id": authorization_id, "status": "NOT_FOUND"}
     6. If found, package into a dict:
        forensic_data = dict(zip(columns, result))
        forensic_data["status"] = "SUCCESS"
        return forensic_data
     7. Wrap in try/except to return:
        {"authorization_id": authorization_id, "status": "FAILED", "error_message": str(e)}
    """
    try:
        conn = duckdb.connect(db_path, read_only=True)
        query = """
            SELECT
                b.authorization_id,
                b.reconciliation_status,
                b.auth_amount_minor,
                b.settled_amount_minor,
                b.discrepancy_amount_minor,
                b.discrepancy_amount_scaled,
                b.is_actionable_break,
                a.merchant_key,
                a.customer_key,
                a.auth_status
            FROM fact_reconciliation_breaks b
            LEFT JOIN fact_card_authorizations a ON b.authorization_id = a.authorization_id
            WHERE b.authorization_id = ?;
        """
        result = conn.execute(query, [authorization_id]).fetchone()
        columns = [desc[0] for desc in conn.description]
        conn.close()
        if result is None:
            return {"authorization_id": authorization_id, "status": "NOT_FOUND"}
        forensic_data = dict(zip(columns, result))
        forensic_data["status"] = "SUCCESS"
        return forensic_data
    except Exception as e:
        print(f"Error fetching break forensics for {authorization_id}: {e}")
        return {"authorization_id": authorization_id, "status": "FAILED", "error_message": str(e)}
