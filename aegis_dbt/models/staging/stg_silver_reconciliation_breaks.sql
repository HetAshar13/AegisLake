{{ config(materialized='view') }}

/*
  Staging View: stg_silver_reconciliation_breaks
  Direct connection to PySpark Three-Way Reconciliation Delta table.
*/

select
    authorization_id,
    reconciliation_status,
    currency,
    coalesce(auth_amount_minor, 0) as auth_amount_minor,
    coalesce(settled_amount_minor, 0) as settled_amount_minor,
    coalesce(discrepancy_amount, 0) as discrepancy_amount_minor,
    reconciled_at
from {{ source('delta_lakehouse', 'silver_reconciliation_breaks') }}
