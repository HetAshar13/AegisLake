{{ config(materialized='table') }}

/*
  Fact: fact_reconciliation_breaks
  Grain: Exactly one row per reconciliation assessment.
  Type: Financial Variance Fact Table.
  Purpose: Governs financial discrepancies across authorizations, settlements,
           and ledger for operations and compliance dispute resolution.
*/

-- TODO [YOUR TURN TO CODE]:
-- 1. Create a CTE `raw_reconciliation_events` with 5 seed rows using UNION ALL:
--    Columns:
--      - reconciliation_id: string
--      - authorization_id: string
--      - currency: string
--      - auth_amount_minor: bigint (or cast(null as bigint))
--      - settled_amount_minor: bigint (or cast(null as bigint))
--      - reconciliation_status: string
--      - reconciled_at: string

WITH raw_reconciliation_events AS (
  SELECT 'REC_001' AS reconciliation_id, 'AUTH_001' AS authorization_id, 'EUR' AS currency, 4500 AS auth_amount_minor, 4500 AS settled_amount_minor, 'MATCHED' AS reconciliation_status, '2026-03-15 15:00:00' AS reconciled_at
  UNION ALL SELECT 'REC_002', 'AUTH_002', 'EUR', 129900, 125000, 'BREAK_AMOUNT_MISMATCH', '2026-07-20 11:00:00'
  UNION ALL SELECT 'REC_003', 'AUTH_003', 'USD', 2450, 2450, 'BREAK_CURRENCY_MISMATCH', '2026-04-10 18:30:00'
  UNION ALL SELECT 'REC_004', 'AUTH_004', 'EUR', 6500, cast(null as bigint), 'BREAK_UNMATCHED_AUTHORIZATION', '2026-09-05 09:00:00'
  UNION ALL SELECT 'REC_005', 'AUTH_UNKNOWN', 'GBP', cast(null as bigint), 3200, 'BREAK_UNMATCHED_SETTLEMENT', '2026-05-12 12:30:00'
)
  
--    Rows to create (covering all 5 status types!):
--      - ('REC_001', 'AUTH_001', 'EUR', 4500, 4500, 'MATCHED', '2026-03-15 15:00:00')
--      - ('REC_002', 'AUTH_002', 'EUR', 129900, 125000, 'BREAK_AMOUNT_MISMATCH', '2026-07-20 11:00:00')
--      - ('REC_003', 'AUTH_003', 'USD', 2450, 2450, 'BREAK_CURRENCY_MISMATCH', '2026-04-10 18:30:00')
--      - ('REC_004', 'AUTH_004', 'EUR', 6500, cast(null as bigint), 'BREAK_UNMATCHED_AUTHORIZATION', '2026-09-05 09:00:00')
--      - ('REC_005', 'AUTH_UNKNOWN', 'GBP', cast(null as bigint), 3200, 'BREAK_UNMATCHED_SETTLEMENT', '2026-05-12 12:30:00')
--
-- 2. Write the final query in strict SQL clause order:
--
--    SELECT
--      - md5(r.reconciliation_id) as break_key (Surrogate Key)
--      - r.authorization_id
--      - r.reconciliation_status
--      - c.currency_key (Foreign Key from dim_currencies)
--      - coalesce(r.auth_amount_minor, 0) as auth_amount_minor
--      - coalesce(r.settled_amount_minor, 0) as settled_amount_minor
--      - (coalesce(r.settled_amount_minor, 0) - coalesce(r.auth_amount_minor, 0)) as discrepancy_amount_minor
--      - (cast(coalesce(r.settled_amount_minor, 0) - coalesce(r.auth_amount_minor, 0) as double) / power(10, c.currency_exponent)) as discrepancy_amount_scaled
--      - (r.reconciliation_status != 'MATCHED') as is_actionable_break
--      - cast(r.reconciled_at as timestamp) as reconciled_at
--      - current_timestamp as created_at
--
--    FROM raw_reconciliation_events r
--
--    JOIN {{ ref('dim_currencies') }} c ON r.currency = c.currency_code

SELECT 
md5(r.reconciliation_id) AS break_key,
r.authorization_id, r.reconciliation_status, c.currency_key,
coalesce(r.auth_amount_minor, 0) AS auth_amount_minor,
coalesce(r.settled_amount_minor, 0) AS settled_amount_minor,
(coalesce(r.settled_amount_minor, 0) - coalesce(r.auth_amount_minor, 0)) AS discrepancy_amount_minor,
(cast(coalesce(r.settled_amount_minor, 0) - coalesce(r.auth_amount_minor, 0) as double) / power(10, c.currency_exponent)) AS discrepancy_amount_scaled,
(r.reconciliation_status != 'MATCHED') AS is_actionable_break,
cast(r.reconciled_at as timestamp) AS reconciled_at,
current_timestamp AS created_at
FROM raw_reconciliation_events r

JOIN {{ ref('dim_currencies') }} c ON r.currency = c.currency_code