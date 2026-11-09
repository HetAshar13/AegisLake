/*
  Singular Data Test: assert_balanced_ledger.sql
  
  Regulatory Rule (BCBS 239 & SOX Invariant):
  In double-entry financial reconciliation:
  1. Any transaction classified as 'MATCHED' MUST have discrepancy_amount_minor = 0.
  2. For all transactions, discrepancy_amount_minor MUST strictly equal (settled_amount_minor - auth_amount_minor).

  dbt Singular Test Convention:
  - If this query returns ZERO rows, the test PASSES!
  - If this query returns ANY rows, those rows represent accounting violations, and the test FAILS!
*/

-- TODO [YOUR TURN TO CODE]:
-- Write a SELECT query querying {{ ref('fact_reconciliation_breaks') }}:
-- Return authorization_id, reconciliation_status, discrepancy_amount_minor
-- WHERE:
--   (reconciliation_status = 'MATCHED' AND discrepancy_amount_minor != 0)
--   OR (discrepancy_amount_minor != (settled_amount_minor - auth_amount_minor))
SELECT
    authorization_id,
    reconciliation_status,
    discrepancy_amount_minor
FROM {{ ref('fact_reconciliation_breaks') }}
WHERE
    (reconciliation_status = 'MATCHED' AND discrepancy_amount_minor != 0)
    OR (discrepancy_amount_minor != (settled_amount_minor - auth_amount_minor))